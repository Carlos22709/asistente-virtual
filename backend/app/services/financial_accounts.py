"""Calcula vencimientos y resumenes de tarjetas y prestamos."""

from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.enums import FinancialAccountType
from ..models.financial_account import FinancialAccount
from ..schemas.financial_account import FinancialAccountRead, FinancialAccountsSummary


def _next_occurrence(today: date, day: int) -> date:
    candidate_day = min(day, monthrange(today.year, today.month)[1])
    candidate = date(today.year, today.month, candidate_day)
    if candidate >= today:
        return candidate
    if today.month == 12:
        year, month = today.year + 1, 1
    else:
        year, month = today.year, today.month + 1
    return date(year, month, min(day, monthrange(year, month)[1]))


def account_to_read(account: FinancialAccount, today: date) -> FinancialAccountRead:
    available = None
    next_statement = None
    if account.account_type == FinancialAccountType.credit_card:
        available = Decimal(account.credit_limit or 0) - Decimal(account.balance)
        if account.statement_day is not None:
            next_statement = _next_occurrence(today, account.statement_day)
    interest = (
        Decimal(account.balance) * Decimal(account.annual_interest_rate) / Decimal("1200")
    ).quantize(Decimal("0.01"))
    return FinancialAccountRead(
        id=account.id,
        name=account.name,
        account_type=account.account_type,
        balance=account.balance,
        credit_limit=account.credit_limit,
        annual_interest_rate=account.annual_interest_rate,
        statement_day=account.statement_day,
        payment_due_day=account.payment_due_day,
        minimum_payment=account.minimum_payment,
        available_credit=available,
        estimated_monthly_interest=interest,
        next_statement_date=next_statement,
        next_payment_due_date=_next_occurrence(today, account.payment_due_day),
        created_at=account.created_at,
    )


def build_accounts_summary(db: Session, today: date) -> FinancialAccountsSummary:
    accounts = list(
        db.scalars(select(FinancialAccount).order_by(FinancialAccount.id)).all()
    )
    details = [account_to_read(account, today) for account in accounts]
    return FinancialAccountsSummary(
        total_debt=sum((item.balance for item in details), Decimal("0")),
        total_available_credit=sum(
            (
                item.available_credit
                for item in details
                if item.available_credit is not None
            ),
            Decimal("0"),
        ),
        estimated_monthly_interest=sum(
            (item.estimated_monthly_interest for item in details), Decimal("0")
        ),
        accounts=details,
    )
