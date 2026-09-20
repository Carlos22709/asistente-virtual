"""Calcula progreso, faltantes y resumenes de las metas de ahorro."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.savings_goal import SavingsGoal
from ..schemas.savings_goal import SavingsGoalRead, SavingsGoalsSummary


def goal_to_read(goal: SavingsGoal, today: date) -> SavingsGoalRead:
    remaining = max(Decimal(goal.target_amount) - Decimal(goal.current_amount), Decimal("0"))
    percentage = (
        Decimal(goal.current_amount) / Decimal(goal.target_amount) * Decimal("100")
    ).quantize(Decimal("0.1"))
    return SavingsGoalRead(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        remaining_amount=remaining,
        percentage_complete=percentage,
        days_remaining=(goal.target_date - today).days if goal.target_date else None,
        created_at=goal.created_at,
    )


def build_savings_summary(db: Session, today: date) -> SavingsGoalsSummary:
    goals = list(db.scalars(select(SavingsGoal).order_by(SavingsGoal.id)).all())
    details = [goal_to_read(goal, today) for goal in goals]
    target = sum((item.target_amount for item in details), Decimal("0"))
    saved = sum((item.current_amount for item in details), Decimal("0"))
    remaining = sum((item.remaining_amount for item in details), Decimal("0"))
    percentage = (
        (saved / target * Decimal("100")).quantize(Decimal("0.1"))
        if target
        else Decimal("0")
    )
    return SavingsGoalsSummary(
        total_target=target,
        total_saved=saved,
        total_remaining=remaining,
        percentage_complete=percentage,
        goals=details,
    )
