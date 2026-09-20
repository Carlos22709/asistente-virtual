"""Respuestas agregadas compartidas por los modulos financieros."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class Message(BaseModel):
    detail: str


class FinanceSummary(BaseModel):
    today: Decimal
    week: Decimal
    month: Decimal


class CashFlowSummary(BaseModel):
    income_month: Decimal
    expenses_month: Decimal
    net_month: Decimal
    projected_recurring_income: Decimal
    projected_recurring_expenses: Decimal
    projected_obligations: Decimal
    projected_available: Decimal
    obligations_due_count: int
    unconfigured_obligations_count: int
    projection_end_date: date


class CashFlowForecastPoint(BaseModel):
    period_start: date
    period_end: date
    recorded_income: Decimal
    recorded_expenses: Decimal
    recurring_income: Decimal
    recurring_expenses: Decimal
    debt_obligations: Decimal
    projected_net: Decimal
    projected_available: Decimal
    unconfigured_obligations_count: int


class CashFlowForecast(BaseModel):
    generated_at: date
    months: int
    points: list[CashFlowForecastPoint]
