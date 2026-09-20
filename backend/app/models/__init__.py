"""Exporta todos los modelos para que SQLAlchemy registre sus tablas."""

from .budget import Budget
from .bank_notification import BankNotification
from .event import Event
from .expense import Expense
from .financial_account import FinancialAccount
from .income import Income
from .recurring_transaction import RecurringTransaction
from .savings_goal import SavingsGoal
from .task import Task

__all__ = [
    "BankNotification",
    "Budget",
    "Event",
    "Expense",
    "FinancialAccount",
    "Income",
    "RecurringTransaction",
    "SavingsGoal",
    "Task",
]
