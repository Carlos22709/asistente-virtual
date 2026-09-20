"""Contratos de lectura y escritura de gastos."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.enums import ExpenseCategory


class ExpenseBase(BaseModel):
    description: str = Field(min_length=1, max_length=180)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    category: ExpenseCategory
    date: date
    note: str | None = None

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La descripción no puede estar vacía")
        return value.strip()


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(ExpenseBase):
    pass


class ExpenseRead(ExpenseBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
