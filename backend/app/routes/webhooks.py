"""Webhook autenticado que convierte alertas bancarias en gastos."""

from functools import lru_cache
from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..schemas.bank_webhook import BankWebhookRequest, BankWebhookResponse
from ..schemas.expense import ExpenseRead
from ..services.bank_ingestion import (
    BankNotificationParser,
    ingest_extraction,
)
from ..services.llm import (
    InvalidLLMResponseError,
    LLMUnavailableError,
    OllamaToolCallingClient,
)

router = APIRouter(prefix="/webhooks", tags=["Automatización"])


@lru_cache
def get_bank_parser() -> BankNotificationParser:
    settings = get_settings()
    client = OllamaToolCallingClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    return BankNotificationParser(client)


def verify_webhook_token(
    x_webhook_token: Annotated[str | None, Header(alias="X-Webhook-Token")] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.bank_webhook_token
    if not expected:
        raise HTTPException(status_code=503, detail="El webhook bancario no está configurado")
    if not x_webhook_token or not compare_digest(x_webhook_token, expected):
        raise HTTPException(status_code=401, detail="Token de webhook inválido")


@router.get(
    "/bank-transactions/status",
    dependencies=[Depends(verify_webhook_token)],
)
def bank_webhook_status(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    return {"status": "ready", "model": settings.ollama_model}


@router.post(
    "/bank-transactions",
    response_model=BankWebhookResponse,
    dependencies=[Depends(verify_webhook_token)],
)
async def ingest_bank_transaction(
    payload: BankWebhookRequest,
    db: Annotated[Session, Depends(get_db)],
    parser: Annotated[BankNotificationParser, Depends(get_bank_parser)],
) -> BankWebhookResponse:
    try:
        extraction = await parser.parse(payload.text)
        result = ingest_extraction(db, payload, extraction)
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Ollama no está disponible") from exc
    except InvalidLLMResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail="No fue posible extraer una transacción válida de la notificación",
        ) from exc

    return BankWebhookResponse(
        status=result.status,
        message=result.message,
        transaction_id=result.notification.id if result.notification else None,
        expense=ExpenseRead.model_validate(result.expense) if result.expense else None,
        extracted=extraction,
    )
