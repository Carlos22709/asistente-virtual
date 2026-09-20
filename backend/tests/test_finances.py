"""Pruebas de recurrencias y proyecciones de flujo de caja."""

import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models.enums import (
    ExpenseCategory,
    FinancialAccountType,
    IncomeCategory,
    RecurrenceFrequency,
    TransactionKind,
)
from app.models.expense import Expense
from app.models.financial_account import FinancialAccount
from app.models.income import Income
from app.models.recurring_transaction import RecurringTransaction
from app.services.finances import (
    build_cash_flow_forecast,
    build_cash_flow_summary,
    recurring_totals_between,
)


class CashFlowProjectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_projects_only_configured_obligations_due_before_month_end(self) -> None:
        today = date(2026, 9, 19)
        self.db.add_all(
            [
                Income(
                    description="Salario",
                    amount=Decimal("1000000.00"),
                    category=IncomeCategory.salary,
                    date=today,
                ),
                Expense(
                    description="Arriendo",
                    amount=Decimal("200000.00"),
                    category=ExpenseCategory.other,
                    date=today,
                ),
                FinancialAccount(
                    name="Tarjeta",
                    account_type=FinancialAccountType.credit_card,
                    balance=Decimal("300000.00"),
                    credit_limit=Decimal("1000000.00"),
                    statement_day=15,
                    payment_due_day=30,
                    minimum_payment=Decimal("50000.00"),
                ),
                FinancialAccount(
                    name="Préstamo corto",
                    account_type=FinancialAccountType.loan,
                    balance=Decimal("100000.00"),
                    payment_due_day=20,
                    minimum_payment=Decimal("250000.00"),
                ),
                FinancialAccount(
                    name="Deuda sin cuota",
                    account_type=FinancialAccountType.loan,
                    balance=Decimal("400000.00"),
                    payment_due_day=25,
                    minimum_payment=None,
                ),
                FinancialAccount(
                    name="Pago del próximo mes",
                    account_type=FinancialAccountType.loan,
                    balance=Decimal("500000.00"),
                    payment_due_day=10,
                    minimum_payment=Decimal("90000.00"),
                ),
            ]
        )
        self.db.commit()

        summary = build_cash_flow_summary(self.db, today)

        self.assertEqual(summary.net_month, Decimal("800000.00"))
        self.assertEqual(summary.projected_obligations, Decimal("150000.00"))
        self.assertEqual(summary.projected_available, Decimal("650000.00"))
        self.assertEqual(summary.obligations_due_count, 2)
        self.assertEqual(summary.unconfigured_obligations_count, 1)
        self.assertEqual(summary.projection_end_date, date(2026, 9, 30))

    def test_clamps_payment_day_to_last_day_of_short_month(self) -> None:
        today = date(2026, 2, 20)
        self.db.add(
            FinancialAccount(
                name="Pago fin de mes",
                account_type=FinancialAccountType.loan,
                balance=Decimal("80000.00"),
                payment_due_day=31,
                minimum_payment=Decimal("20000.00"),
            )
        )
        self.db.commit()

        summary = build_cash_flow_summary(self.db, today)

        self.assertEqual(summary.projected_obligations, Decimal("20000.00"))
        self.assertEqual(summary.projected_available, Decimal("-20000.00"))
        self.assertEqual(summary.projection_end_date, date(2026, 2, 28))

    def test_recurring_monthly_rule_clamps_to_short_month(self) -> None:
        self.db.add(
            RecurringTransaction(
                description="Arriendo",
                amount=Decimal("800000.00"),
                kind=TransactionKind.expense,
                category=ExpenseCategory.other.value,
                frequency=RecurrenceFrequency.monthly,
                interval=1,
                start_date=date(2026, 1, 31),
                active=True,
            )
        )
        self.db.commit()

        income, expenses = recurring_totals_between(
            self.db, date(2026, 2, 1), date(2026, 2, 28)
        )

        self.assertEqual(income, Decimal("0"))
        self.assertEqual(expenses, Decimal("800000.00"))
        _, march_expenses = recurring_totals_between(
            self.db, date(2026, 3, 29), date(2026, 3, 31)
        )
        self.assertEqual(march_expenses, Decimal("800000.00"))

    def test_builds_accumulated_multi_month_forecast(self) -> None:
        today = date(2026, 9, 19)
        self.db.add_all(
            [
                Income(
                    description="Ingreso actual",
                    amount=Decimal("500.00"),
                    category=IncomeCategory.other,
                    date=today,
                ),
                Expense(
                    description="Gasto actual",
                    amount=Decimal("50.00"),
                    category=ExpenseCategory.other,
                    date=today,
                ),
                RecurringTransaction(
                    description="Servicio",
                    amount=Decimal("100.00"),
                    kind=TransactionKind.expense,
                    category=ExpenseCategory.other.value,
                    frequency=RecurrenceFrequency.monthly,
                    interval=1,
                    start_date=date(2026, 9, 25),
                    active=True,
                ),
                RecurringTransaction(
                    description="Salario",
                    amount=Decimal("1000.00"),
                    kind=TransactionKind.income,
                    category=IncomeCategory.salary.value,
                    frequency=RecurrenceFrequency.monthly,
                    interval=1,
                    start_date=date(2026, 10, 1),
                    active=True,
                ),
                FinancialAccount(
                    name="Préstamo corto",
                    account_type=FinancialAccountType.loan,
                    balance=Decimal("250.00"),
                    payment_due_day=30,
                    minimum_payment=Decimal("100.00"),
                ),
            ]
        )
        self.db.commit()

        forecast = build_cash_flow_forecast(self.db, today, 2)

        self.assertEqual(forecast.points[0].projected_net, Decimal("250.00"))
        self.assertEqual(forecast.points[0].projected_available, Decimal("250.00"))
        self.assertEqual(forecast.points[1].projected_net, Decimal("800.00"))
        self.assertEqual(forecast.points[1].projected_available, Decimal("1050.00"))


if __name__ == "__main__":
    unittest.main()
