"""Endpoints CRUD para presupuestos mensuales."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.budget import Budget
from ..schemas.budget import BudgetCreate, BudgetRead, BudgetUpdate, CurrentBudget
from ..services.budgets import get_budget_summary
from ..services.clock import bogota_today

router = APIRouter(prefix="/budgets", tags=["Presupuestos"])


def get_or_404(db: Session, budget_id: int) -> Budget:
    budget = db.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return budget


@router.get("/current", response_model=CurrentBudget | None)
def current_budget(db: Session = Depends(get_db)) -> CurrentBudget | None:
    return get_budget_summary(db, bogota_today())


@router.get("", response_model=list[BudgetRead])
def list_budgets(db: Session = Depends(get_db)) -> list[Budget]:
    return list(db.scalars(select(Budget).order_by(Budget.year.desc(), Budget.month.desc())).all())


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def create_budget(payload: BudgetCreate, db: Session = Depends(get_db)) -> Budget:
    existing = db.scalar(
        select(Budget).where(Budget.month == payload.month, Budget.year == payload.year)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe un presupuesto para ese mes")
    budget = Budget(**payload.model_dump())
    db.add(budget)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un presupuesto para ese mes")
    db.refresh(budget)
    return budget


@router.put("/{budget_id}", response_model=BudgetRead)
def update_budget(
    budget_id: int, payload: BudgetUpdate, db: Session = Depends(get_db)
) -> Budget:
    budget = get_or_404(db, budget_id)
    budget.amount = payload.amount
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: int, db: Session = Depends(get_db)) -> Response:
    budget = get_or_404(db, budget_id)
    db.delete(budget)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
