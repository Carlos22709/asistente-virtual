"""Contratos para metas de ahorro, aportes y resumenes."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class SavingsGoalBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    current_amount: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=14, decimal_places=2
    )
    target_date: date | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El nombre no puede estar vacío")
        return value.strip()


class SavingsGoalCreate(SavingsGoalBase):
    pass


class SavingsGoalUpdate(SavingsGoalBase):
    pass


class SavingsContribution(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class SavingsGoalRead(SavingsGoalBase):
    id: int
    remaining_amount: Decimal
    percentage_complete: Decimal
    days_remaining: int | None
    created_at: datetime


class SavingsGoalsSummary(BaseModel):
    total_target: Decimal
    total_saved: Decimal
    total_remaining: Decimal
    percentage_complete: Decimal
    goals: list[SavingsGoalRead]
