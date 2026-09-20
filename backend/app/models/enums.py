"""Enumeraciones compartidas por el dominio de secretaria y finanzas."""

from enum import Enum


class TaskPriority(str, Enum):
    low = "Baja"
    medium = "Media"
    high = "Alta"


class TaskStatus(str, Enum):
    pending = "Pendiente"
    in_progress = "En progreso"
    completed = "Completada"


class ExpenseCategory(str, Enum):
    food = "Comida"
    transport = "Transporte"
    university = "Universidad"
    entertainment = "Entretenimiento"
    shopping = "Compras"
    health = "Salud"
    other = "Otros"


class IncomeCategory(str, Enum):
    salary = "Salario"
    freelance = "Trabajo independiente"
    scholarship = "Beca"
    family = "Apoyo familiar"
    refund = "Reembolso"
    investment = "Inversión"
    other = "Otros"


class FinancialAccountType(str, Enum):
    credit_card = "Tarjeta de crédito"
    loan = "Préstamo"


class TransactionKind(str, Enum):
    income = "Ingreso"
    expense = "Gasto"


class RecurrenceFrequency(str, Enum):
    weekly = "Semanal"
    monthly = "Mensual"
    yearly = "Anual"
