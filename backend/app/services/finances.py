"""Calcula totales, flujo de caja y proyecciones financieras mensuales."""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.enums import TransactionKind
from ..models.expense import Expense
from ..models.financial_account import FinancialAccount
from ..models.income import Income
from ..models.recurring_transaction import RecurringTransaction
from ..schemas.common import (
    CashFlowForecast,
    CashFlowForecastPoint,
    CashFlowSummary,
    FinanceSummary,
)
from .financial_accounts import account_to_read


def total_between(db: Session, start: date, end: date) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.date >= start, Expense.date <= end
        )
    )
    return Decimal(value or 0)


def income_total_between(db: Session, start: date, end: date) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(Income.amount), 0)).where(
            Income.date >= start, Income.date <= end
        )
    )
    return Decimal(value or 0)


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _recurring_occurrence(
    rule: RecurringTransaction, occurrence_index: int
) -> date:
    if rule.frequency.value == "Semanal":
        return rule.start_date + timedelta(
            weeks=rule.interval * occurrence_index
        )
    if rule.frequency.value == "Mensual":
        return _add_months(rule.start_date, rule.interval * occurrence_index)
    target_year = rule.start_date.year + rule.interval * occurrence_index
    return date(
        target_year,
        rule.start_date.month,
        min(
            rule.start_date.day,
            monthrange(target_year, rule.start_date.month)[1],
        ),
    )


def recurring_totals_between(
    db: Session, start: date, end: date
) -> tuple[Decimal, Decimal]:
    """Suma las ocurrencias activas que caen dentro del intervalo."""

    if end < start:
        return Decimal(0), Decimal(0)
    rules = list(
        db.scalars(
            select(RecurringTransaction).where(
                RecurringTransaction.active.is_(True),
                RecurringTransaction.start_date <= end,
            )
        ).all()
    )
    income = Decimal(0)
    expenses = Decimal(0)
    for rule in rules:
        occurrence_index = 0
        occurrence = _recurring_occurrence(rule, occurrence_index)
        rule_end = min(end, rule.end_date) if rule.end_date else end
        while occurrence < start:
            occurrence_index += 1
            occurrence = _recurring_occurrence(rule, occurrence_index)
        while occurrence <= rule_end:
            if rule.kind == TransactionKind.income:
                income += Decimal(rule.amount)
            else:
                expenses += Decimal(rule.amount)
            occurrence_index += 1
            occurrence = _recurring_occurrence(rule, occurrence_index)
    return income, expenses


def build_finance_summary(db: Session, today: date) -> FinanceSummary:
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    return FinanceSummary(
        today=total_between(db, today, today),
        week=total_between(db, week_start, today),
        month=total_between(db, month_start, today),
    )


def build_cash_flow_summary(db: Session, today: date) -> CashFlowSummary:
    """Combina movimientos reales y programados para el cierre del mes."""

    month_start = today.replace(day=1)
    month_end = today.replace(day=monthrange(today.year, today.month)[1])
    income = income_total_between(db, month_start, today)
    expenses = total_between(db, month_start, today)
    net = income - expenses
    recurring_income, recurring_expenses = recurring_totals_between(
        db, today + timedelta(days=1), month_end
    )

    accounts = list(
        db.scalars(select(FinancialAccount).order_by(FinancialAccount.id)).all()
    )
    projected_obligations = Decimal(0)
    obligations_due_count = 0
    unconfigured_obligations_count = 0
    for account in accounts:
        balance = Decimal(account.balance)
        if balance <= 0:
            continue
        detail = account_to_read(account, today)
        if detail.next_payment_due_date > month_end:
            continue
        if account.minimum_payment is None:
            unconfigured_obligations_count += 1
            continue
        projected_obligations += min(balance, Decimal(account.minimum_payment))
        obligations_due_count += 1

    return CashFlowSummary(
        income_month=income,
        expenses_month=expenses,
        net_month=net,
        projected_recurring_income=recurring_income,
        projected_recurring_expenses=recurring_expenses,
        projected_obligations=projected_obligations,
        projected_available=(
            net + recurring_income - recurring_expenses - projected_obligations
        ),
        obligations_due_count=obligations_due_count,
        unconfigured_obligations_count=unconfigured_obligations_count,
        projection_end_date=month_end,
    )


def build_cash_flow_forecast(
    db: Session, today: date, months: int
) -> CashFlowForecast:
    """Proyecta el disponible acumulado y amortiza deudas mes a mes."""

    points: list[CashFlowForecastPoint] = []
    running_available = Decimal(0)
    accounts = list(
        db.scalars(select(FinancialAccount).order_by(FinancialAccount.id)).all()
    )
    remaining_debt = {account.id: Decimal(account.balance) for account in accounts}

    for offset in range(months):
        period_start = _add_months(today.replace(day=1), offset)
        period_end = period_start.replace(
            day=monthrange(period_start.year, period_start.month)[1]
        )
        recorded_end = today if offset == 0 else period_end
        recorded_income = income_total_between(db, period_start, recorded_end)
        recorded_expenses = total_between(db, period_start, recorded_end)
        recurring_start = today + timedelta(days=1) if offset == 0 else period_start
        recurring_income, recurring_expenses = recurring_totals_between(
            db, recurring_start, period_end
        )

        obligations = Decimal(0)
        unconfigured = 0
        # Cada pago reduce el saldo usado en los meses siguientes de la proyeccion.
        for account in accounts:
            balance = remaining_debt[account.id]
            if balance <= 0:
                continue
            if offset == 0:
                due_date = account_to_read(account, today).next_payment_due_date
                if due_date > period_end:
                    continue
            if account.minimum_payment is None:
                unconfigured += 1
                continue
            payment = min(balance, Decimal(account.minimum_payment))
            obligations += payment
            remaining_debt[account.id] = balance - payment

        projected_net = (
            recorded_income
            + recurring_income
            - recorded_expenses
            - recurring_expenses
            - obligations
        )
        running_available += projected_net
        points.append(
            CashFlowForecastPoint(
                period_start=period_start,
                period_end=period_end,
                recorded_income=recorded_income,
                recorded_expenses=recorded_expenses,
                recurring_income=recurring_income,
                recurring_expenses=recurring_expenses,
                debt_obligations=obligations,
                projected_net=projected_net,
                projected_available=running_available,
                unconfigured_obligations_count=unconfigured,
            )
        )

    return CashFlowForecast(generated_at=today, months=months, points=points)
