"""Contratos y validaciones para notificaciones bancarias entrantes."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from ..models.enums import ExpenseCategory
from .expense import ExpenseRead


class BankWebhookRequest(BaseModel):
    text: str = Field(min_length=10, max_length=12000)
    source: str = Field(default="mobile_automation", min_length=1, max_length=80)

    @field_validator("text", "source")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class BankTransactionExtraction(BaseModel):
    is_transaction: bool
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    merchant: str | None = Field(default=None, min_length=1, max_length=180)
    transaction_date: date | None = None
    category: ExpenseCategory | None = None
    payment_method: str | None = Field(default=None, max_length=120)
    external_reference: str | None = Field(default=None, max_length=120)
    reason: str = Field(min_length=1, max_length=300)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("merchant", "payment_method", "external_reference")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @model_validator(mode="after")
    def require_transaction_fields(self) -> "BankTransactionExtraction":
        if self.is_transaction:
            required = (
                self.amount,
                self.currency,
                self.merchant,
                self.transaction_date,
                self.category,
            )
            if any(value is None for value in required):
                raise ValueError("Una transacción requiere monto, moneda, comercio, fecha y categoría")
        return self


class BankWebhookResponse(BaseModel):
    status: Literal["created", "duplicate", "ignored"]
    message: str
    transaction_id: int | None = None
    expense: ExpenseRead | None = None
    extracted: BankTransactionExtraction
