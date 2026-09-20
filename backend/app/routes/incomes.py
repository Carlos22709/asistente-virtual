"""Endpoints CRUD y flujo de caja para ingresos."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.enums import IncomeCategory
from ..models.income import Income
from ..schemas.common import CashFlowSummary
from ..schemas.income import IncomeCreate, IncomeRead, IncomeUpdate
from ..services.clock import bogota_today
from ..services.finances import build_cash_flow_summary

router = APIRouter(prefix="/incomes", tags=["Ingresos"])


def get_or_404(db: Session, income_id: int) -> Income:
    income = db.get(Income, income_id)
    if not income:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado")
    return income


@router.get("/cash-flow", response_model=CashFlowSummary)
def cash_flow(db: Session = Depends(get_db)) -> CashFlowSummary:
    return build_cash_flow_summary(db, bogota_today())


@router.get("", response_model=list[IncomeRead])
def list_incomes(
    category: IncomeCategory | None = None,
    income_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> list[Income]:
    query = select(Income)
    if category is not None:
        query = query.where(Income.category == category)
    if income_date is not None:
        query = query.where(Income.date == income_date)
    if date_from is not None:
        query = query.where(Income.date >= date_from)
    if date_to is not None:
        query = query.where(Income.date <= date_to)
    return list(
        db.scalars(query.order_by(Income.date.desc(), Income.created_at.desc())).all()
    )


@router.post("", response_model=IncomeRead, status_code=status.HTTP_201_CREATED)
def create_income(payload: IncomeCreate, db: Session = Depends(get_db)) -> Income:
    income = Income(**payload.model_dump())
    db.add(income)
    db.commit()
    db.refresh(income)
    return income


@router.get("/{income_id}", response_model=IncomeRead)
def get_income(income_id: int, db: Session = Depends(get_db)) -> Income:
    return get_or_404(db, income_id)


@router.put("/{income_id}", response_model=IncomeRead)
def update_income(
    income_id: int, payload: IncomeUpdate, db: Session = Depends(get_db)
) -> Income:
    income = get_or_404(db, income_id)
    for key, value in payload.model_dump().items():
        setattr(income, key, value)
    db.commit()
    db.refresh(income)
    return income


@router.delete("/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income(income_id: int, db: Session = Depends(get_db)) -> Response:
    income = get_or_404(db, income_id)
    db.delete(income)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
