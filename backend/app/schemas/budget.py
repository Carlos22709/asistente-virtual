"""Contratos de lectura y escritura de presupuestos."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BudgetBase(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2200)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class BudgetRead(BudgetBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CurrentBudget(BudgetRead):
    spent: Decimal
    available: Decimal
    percentage_used: Decimal
