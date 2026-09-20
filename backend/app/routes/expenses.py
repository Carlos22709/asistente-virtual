"""Endpoints CRUD y resumen para gastos."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.enums import ExpenseCategory
from ..models.expense import Expense
from ..schemas.common import FinanceSummary
from ..schemas.expense import ExpenseCreate, ExpenseRead, ExpenseUpdate
from ..services.finances import build_finance_summary
from ..services.clock import bogota_today

router = APIRouter(prefix="/expenses", tags=["Gastos"])


def get_or_404(db: Session, expense_id: int) -> Expense:
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return expense


@router.get("/summary", response_model=FinanceSummary)
def expense_summary(db: Session = Depends(get_db)) -> FinanceSummary:
    return build_finance_summary(db, bogota_today())


@router.get("", response_model=list[ExpenseRead])
def list_expenses(
    category: ExpenseCategory | None = None,
    expense_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> list[Expense]:
    query = select(Expense)
    if category is not None:
        query = query.where(Expense.category == category)
    if expense_date is not None:
        query = query.where(Expense.date == expense_date)
    if date_from is not None:
        query = query.where(Expense.date >= date_from)
    if date_to is not None:
        query = query.where(Expense.date <= date_to)
    return list(db.scalars(query.order_by(Expense.date.desc(), Expense.created_at.desc())).all())


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db)) -> Expense:
    expense = Expense(**payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(expense_id: int, db: Session = Depends(get_db)) -> Expense:
    return get_or_404(db, expense_id)


@router.put("/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: int, payload: ExpenseUpdate, db: Session = Depends(get_db)
) -> Expense:
    expense = get_or_404(db, expense_id)
    for key, value in payload.model_dump().items():
        setattr(expense, key, value)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, db: Session = Depends(get_db)) -> Response:
    expense = get_or_404(db, expense_id)
    db.delete(expense)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
