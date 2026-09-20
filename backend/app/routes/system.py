"""Diagnostico del sistema y respaldo/restauracion de los datos del usuario."""

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, Integer, Numeric, select, text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models.bank_notification import BankNotification
from ..models.budget import Budget
from ..models.event import Event
from ..models.expense import Expense
from ..models.financial_account import FinancialAccount
from ..models.income import Income
from ..models.recurring_transaction import RecurringTransaction
from ..models.savings_goal import SavingsGoal
from ..models.task import Task
from ..schemas.system import (
    BackupDocument,
    BackupRestoreRequest,
    BackupRestoreResult,
    ComponentStatus,
    SystemStatus,
)

router = APIRouter(prefix="/system", tags=["Sistema"])

BACKUP_MODELS = {
    "tasks": Task,
    "expenses": Expense,
    "incomes": Income,
    "budgets": Budget,
    "events": Event,
    "financial_accounts": FinancialAccount,
    "savings_goals": SavingsGoal,
    "recurring_transactions": RecurringTransaction,
    "bank_notifications": BankNotification,
}


@router.get("/status", response_model=SystemStatus)
async def system_status(db: Session = Depends(get_db)) -> SystemStatus:
    settings = get_settings()
    components: dict[str, ComponentStatus] = {}

    try:
        db.execute(text("SELECT 1"))
        components["database"] = ComponentStatus(
            status="ready", detail="La base de datos respondió correctamente."
        )
    except Exception:
        components["database"] = ComponentStatus(
            status="error", detail="La base de datos no está disponible."
        )

    try:
        async with httpx.AsyncClient(timeout=min(settings.llm_timeout_seconds, 5)) as client:
            response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
        components["ollama"] = ComponentStatus(
            status="ready",
            detail=f"Ollama está disponible con el modelo configurado {settings.ollama_model}.",
        )
    except (httpx.RequestError, httpx.HTTPStatusError):
        components["ollama"] = ComponentStatus(
            status="error", detail="Ollama no respondió en la URL configurada."
        )

    gmail_token = Path(settings.gmail_token_file)
    components["gmail"] = ComponentStatus(
        status="ready" if gmail_token.is_file() else "missing",
        detail=(
            "Gmail tiene un token local de autorización."
            if gmail_token.is_file()
            else "Gmail todavía necesita autorización."
        ),
    )
    components["bank_webhook"] = ComponentStatus(
        status="ready" if settings.bank_webhook_token else "missing",
        detail=(
            "El webhook bancario está protegido y listo."
            if settings.bank_webhook_token
            else "Falta configurar BANK_WEBHOOK_TOKEN."
        ),
    )

    critical_ready = all(
        components[name].status == "ready" for name in ("database", "ollama")
    )
    provider = (
        "supabase"
        if settings.uses_supabase
        else "local"
        if settings.uses_local_database
        else "postgresql"
    )
    return SystemStatus(
        status="ready" if critical_ready else "degraded",
        checked_at=datetime.now(timezone.utc),
        database_provider=provider,
        api_auth_enabled=settings.app_api_token is not None,
        components=components,
    )


def _row_data(item: Any) -> dict[str, Any]:
    return {
        column.name: jsonable_encoder(getattr(item, column.name))
        for column in item.__table__.columns
    }


def _coerce_value(column: Any, value: Any) -> Any:
    if value is None:
        return None
    column_type = column.type
    if isinstance(column_type, SAEnum) and column_type.enum_class:
        return column_type.enum_class(value)
    if isinstance(column_type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(column_type, Date) and not isinstance(column_type, DateTime) and isinstance(value, str):
        return date.fromisoformat(value)
    if isinstance(column_type, Numeric):
        return Decimal(str(value))
    if isinstance(column_type, Boolean):
        return bool(value)
    if isinstance(column_type, Integer):
        return int(value)
    return value


@router.get("/backup", response_model=BackupDocument)
def export_backup(db: Session = Depends(get_db)) -> BackupDocument:
    tables = {
        table: [_row_data(item) for item in db.scalars(select(model)).all()]
        for table, model in BACKUP_MODELS.items()
    }
    return BackupDocument(
        exported_at=datetime.now(timezone.utc),
        tables=tables,
    )


@router.post("/backup/restore", response_model=BackupRestoreResult)
def restore_backup(
    payload: BackupRestoreRequest,
    confirmation: str | None = Header(default=None, alias="X-Confirm-Restore"),
    db: Session = Depends(get_db),
) -> BackupRestoreResult:
    if confirmation != "restore":
        raise HTTPException(
            status_code=400,
            detail="La restauración requiere el encabezado X-Confirm-Restore: restore",
        )
    unknown = set(payload.backup.tables) - set(BACKUP_MODELS)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail="La copia contiene tablas desconocidas: " + ", ".join(sorted(unknown)),
        )

    restored: dict[str, int] = {}
    try:
        if payload.replace_existing:
            for model in reversed(list(BACKUP_MODELS.values())):
                db.query(model).delete()
            db.flush()

        for table, model in BACKUP_MODELS.items():
            columns = {column.name: column for column in model.__table__.columns}
            rows = payload.backup.tables.get(table, [])
            restored[table] = 0
            for raw in rows:
                invalid = set(raw) - set(columns)
                if invalid:
                    raise ValueError(
                        f"{table} contiene columnas desconocidas: {', '.join(sorted(invalid))}"
                    )
                values = {
                    name: _coerce_value(columns[name], value)
                    for name, value in raw.items()
                }
                row_id = values.get("id")
                item = db.get(model, row_id) if row_id is not None else None
                if item is None:
                    db.add(model(**values))
                else:
                    for name, value in values.items():
                        setattr(item, name, value)
                restored[table] += 1
            db.flush()

        if db.bind and db.bind.dialect.name == "postgresql":
            for table in BACKUP_MODELS:
                db.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence(:table_name, 'id'), "
                        "COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM " + table
                    ),
                    {"table_name": table},
                )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"No fue posible restaurar la copia: {exc}",
        ) from exc

    return BackupRestoreResult(
        status="restored",
        restored_rows=sum(restored.values()),
        tables=restored,
    )
