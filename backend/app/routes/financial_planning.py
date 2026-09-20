"""Endpoints para transacciones recurrentes y proyecciones de flujo de caja."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.recurring_transaction import RecurringTransaction
from ..schemas.common import CashFlowForecast
from ..schemas.recurring_transaction import (
    RecurringTransactionCreate,
    RecurringTransactionRead,
    RecurringTransactionUpdate,
)
from ..services.clock import bogota_today
from ..services.finances import build_cash_flow_forecast

router = APIRouter(prefix="/finances", tags=["Planificación financiera"])


def get_or_404(db: Session, item_id: int) -> RecurringTransaction:
    item = db.get(RecurringTransaction, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Movimiento recurrente no encontrado")
    return item


@router.get("/forecast", response_model=CashFlowForecast)
def forecast(
    months: int = Query(default=6, ge=1, le=24),
    db: Session = Depends(get_db),
) -> CashFlowForecast:
    return build_cash_flow_forecast(db, bogota_today(), months)


@router.get("/recurring", response_model=list[RecurringTransactionRead])
def list_recurring(db: Session = Depends(get_db)) -> list[RecurringTransaction]:
    return list(
        db.scalars(
            select(RecurringTransaction).order_by(
                RecurringTransaction.active.desc(),
                RecurringTransaction.start_date,
                RecurringTransaction.id,
            )
        ).all()
    )


@router.post(
    "/recurring",
    response_model=RecurringTransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_recurring(
    payload: RecurringTransactionCreate, db: Session = Depends(get_db)
) -> RecurringTransaction:
    item = RecurringTransaction(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/recurring/{item_id}", response_model=RecurringTransactionRead)
def update_recurring(
    item_id: int,
    payload: RecurringTransactionUpdate,
    db: Session = Depends(get_db),
) -> RecurringTransaction:
    item = get_or_404(db, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/recurring/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring(item_id: int, db: Session = Depends(get_db)) -> Response:
    item = get_or_404(db, item_id)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
