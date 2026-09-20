"""Contrato del resumen consolidado mostrado en el inicio."""

from decimal import Decimal

from pydantic import BaseModel

from .budget import CurrentBudget
from .event import EventRead
from .task import TaskRead


class DashboardSummary(BaseModel):
    pending_tasks: int
    upcoming_tasks: list[TaskRead]
    today_spent: Decimal
    week_spent: Decimal
    month_income: Decimal
    month_cash_flow: Decimal
    month_projected_obligations: Decimal
    month_projected_available: Decimal
    unconfigured_obligations_count: int
    next_event: EventRead | None
    current_budget: CurrentBudget | None
