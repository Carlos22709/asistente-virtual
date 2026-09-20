"""Modelo persistente del presupuesto mensual."""

from decimal import Decimal

from sqlalchemy import CheckConstraint, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("month", "year", name="uq_budget_month_year"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_budget_month"),
        CheckConstraint("amount > 0", name="ck_budget_amount"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[int] = mapped_column(nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
