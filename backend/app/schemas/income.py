"""Contratos de lectura y escritura de ingresos."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.enums import IncomeCategory


class IncomeBase(BaseModel):
    description: str = Field(min_length=1, max_length=180)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    category: IncomeCategory
    date: date
    note: str | None = None

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La descripción no puede estar vacía")
        return value.strip()


class IncomeCreate(IncomeBase):
    pass


class IncomeUpdate(IncomeBase):
    pass


class IncomeRead(IncomeBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
