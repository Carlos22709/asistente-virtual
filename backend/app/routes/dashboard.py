"""Endpoint agregado con el resumen principal de la aplicacion."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.event import Event
from ..models.task import Task
from ..schemas.dashboard import DashboardSummary
from ..services.budgets import get_budget_summary
from ..services.clock import bogota_now
from ..services.finances import build_cash_flow_summary, build_finance_summary

router = APIRouter(prefix="/dashboard", tags=["Inicio"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    now = bogota_now()
    today = now.date()
    pending = db.scalar(select(func.count()).select_from(Task).where(Task.completed.is_(False))) or 0
    upcoming_tasks = list(
        db.scalars(
            select(Task)
            .where(Task.completed.is_(False), Task.due_date.is_not(None))
            .order_by(Task.due_date)
            .limit(3)
        ).all()
    )
    next_event = db.scalar(
        select(Event).where(Event.start_datetime >= now).order_by(Event.start_datetime).limit(1)
    )
    finances = build_finance_summary(db, today)
    cash_flow = build_cash_flow_summary(db, today)
    return DashboardSummary(
        pending_tasks=pending,
        upcoming_tasks=upcoming_tasks,
        today_spent=finances.today,
        week_spent=finances.week,
        month_income=cash_flow.income_month,
        month_cash_flow=cash_flow.net_month,
        month_projected_obligations=cash_flow.projected_obligations,
        month_projected_available=cash_flow.projected_available,
        unconfigured_obligations_count=cash_flow.unconfigured_obligations_count,
        next_event=next_event,
        current_budget=get_budget_summary(db, today),
    )
