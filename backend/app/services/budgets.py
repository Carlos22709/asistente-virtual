"""Calcula el consumo y saldo disponible del presupuesto vigente."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.budget import Budget
from ..schemas.budget import CurrentBudget
from .finances import total_between


def get_budget_summary(db: Session, today: date) -> CurrentBudget | None:
    budget = db.scalar(
        select(Budget).where(Budget.month == today.month, Budget.year == today.year)
    )
    if not budget:
        return None
    month_start = today.replace(day=1)
    spent = total_between(db, month_start, today)
    available = budget.amount - spent
    percentage = (spent / budget.amount * Decimal("100")).quantize(Decimal("0.1"))
    return CurrentBudget(
        id=budget.id,
        month=budget.month,
        year=budget.year,
        amount=budget.amount,
        spent=spent,
        available=available,
        percentage_used=percentage,
    )
