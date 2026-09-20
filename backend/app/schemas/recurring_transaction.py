"""Contratos y reglas de recurrencia para movimientos programados."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..models.enums import (
    ExpenseCategory,
    IncomeCategory,
    RecurrenceFrequency,
    TransactionKind,
)


class RecurringTransactionBase(BaseModel):
    description: str = Field(min_length=1, max_length=180)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    kind: TransactionKind
    category: str = Field(min_length=1, max_length=40)
    frequency: RecurrenceFrequency
    interval: int = Field(default=1, ge=1, le=52)
    start_date: date
    end_date: date | None = None
    active: bool = True
    note: str | None = None

    @field_validator("description", "category")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El texto no puede estar vacío")
        return value.strip()

    @model_validator(mode="after")
    def validate_rule(self) -> "RecurringTransactionBase":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("La fecha final no puede ser anterior a la inicial")
        allowed = (
            {item.value for item in IncomeCategory}
            if self.kind == TransactionKind.income
            else {item.value for item in ExpenseCategory}
        )
        if self.category not in allowed:
            raise ValueError("La categoría no corresponde al tipo de movimiento")
        return self


class RecurringTransactionCreate(RecurringTransactionBase):
    pass


class RecurringTransactionUpdate(RecurringTransactionBase):
    pass


class RecurringTransactionRead(RecurringTransactionBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
