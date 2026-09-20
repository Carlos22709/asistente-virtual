"""Contratos de tarjetas de credito, prestamos y sus resumenes."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from ..models.enums import FinancialAccountType


class FinancialAccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    account_type: FinancialAccountType
    balance: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    credit_limit: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    annual_interest_rate: Decimal = Field(
        default=Decimal("0"), ge=0, le=200, max_digits=7, decimal_places=4
    )
    statement_day: int | None = Field(default=None, ge=1, le=31)
    payment_due_day: int = Field(ge=1, le=31)
    minimum_payment: Decimal | None = Field(
        default=None, gt=0, max_digits=14, decimal_places=2
    )

    @model_validator(mode="after")
    def validate_account_details(self) -> "FinancialAccountBase":
        self.name = self.name.strip()
        if self.account_type == FinancialAccountType.credit_card:
            if self.credit_limit is None:
                raise ValueError("Una tarjeta requiere el cupo total")
            if self.statement_day is None:
                raise ValueError("Una tarjeta requiere el día de corte")
        elif self.credit_limit is not None or self.statement_day is not None:
            raise ValueError("Un préstamo no usa cupo ni día de corte")
        return self


class FinancialAccountWrite(FinancialAccountBase):
    @model_validator(mode="after")
    def validate_payment_amount(self) -> "FinancialAccountWrite":
        if self.balance > 0 and self.minimum_payment is None:
            raise ValueError("Una deuda requiere el pago mínimo o la cuota mensual")
        return self


class FinancialAccountCreate(FinancialAccountWrite):
    pass


class FinancialAccountUpdate(FinancialAccountWrite):
    pass


class FinancialAccountRead(FinancialAccountBase):
    id: int
    available_credit: Decimal | None
    estimated_monthly_interest: Decimal
    next_statement_date: date | None
    next_payment_due_date: date
    created_at: datetime


class FinancialAccountsSummary(BaseModel):
    total_debt: Decimal
    total_available_credit: Decimal
    estimated_monthly_interest: Decimal
    accounts: list[FinancialAccountRead]
