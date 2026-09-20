"""Modelo persistente de tarjetas de credito y prestamos."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .enums import FinancialAccountType


class FinancialAccount(Base):
    __tablename__ = "financial_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[FinancialAccountType] = mapped_column(
        Enum(FinancialAccountType, native_enum=False, length=30), nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    annual_interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False, default=Decimal("0")
    )
    statement_day: Mapped[int | None] = mapped_column(Integer)
    payment_due_day: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_payment: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
