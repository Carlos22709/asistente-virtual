"""Endpoints para crear metas de ahorro y registrar aportes."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.savings_goal import SavingsGoal
from ..schemas.savings_goal import (
    SavingsContribution,
    SavingsGoalCreate,
    SavingsGoalRead,
    SavingsGoalsSummary,
    SavingsGoalUpdate,
)
from ..services.clock import bogota_today
from ..services.savings import build_savings_summary, goal_to_read

router = APIRouter(prefix="/savings-goals", tags=["Metas de ahorro"])


def get_or_404(db: Session, goal_id: int) -> SavingsGoal:
    goal = db.get(SavingsGoal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Meta de ahorro no encontrada")
    return goal


def _name_exists(db: Session, name: str, exclude_id: int | None = None) -> bool:
    query = select(SavingsGoal.id).where(func.lower(SavingsGoal.name) == name.lower())
    if exclude_id is not None:
        query = query.where(SavingsGoal.id != exclude_id)
    return db.scalar(query) is not None


@router.get("/summary", response_model=SavingsGoalsSummary)
def savings_summary(db: Session = Depends(get_db)) -> SavingsGoalsSummary:
    return build_savings_summary(db, bogota_today())


@router.get("", response_model=list[SavingsGoalRead])
def list_goals(db: Session = Depends(get_db)) -> list[SavingsGoalRead]:
    return build_savings_summary(db, bogota_today()).goals


@router.post("", response_model=SavingsGoalRead, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: SavingsGoalCreate, db: Session = Depends(get_db)
) -> SavingsGoalRead:
    if _name_exists(db, payload.name):
        raise HTTPException(status_code=409, detail="Ya existe una meta con ese nombre")
    goal = SavingsGoal(**payload.model_dump())
    db.add(goal)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una meta con ese nombre")
    db.refresh(goal)
    return goal_to_read(goal, bogota_today())


@router.get("/{goal_id}", response_model=SavingsGoalRead)
def get_goal(goal_id: int, db: Session = Depends(get_db)) -> SavingsGoalRead:
    return goal_to_read(get_or_404(db, goal_id), bogota_today())


@router.put("/{goal_id}", response_model=SavingsGoalRead)
def update_goal(
    goal_id: int,
    payload: SavingsGoalUpdate,
    db: Session = Depends(get_db),
) -> SavingsGoalRead:
    goal = get_or_404(db, goal_id)
    if _name_exists(db, payload.name, exclude_id=goal_id):
        raise HTTPException(status_code=409, detail="Ya existe una meta con ese nombre")
    for key, value in payload.model_dump().items():
        setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal_to_read(goal, bogota_today())


@router.post("/{goal_id}/contributions", response_model=SavingsGoalRead)
def add_contribution(
    goal_id: int,
    payload: SavingsContribution,
    db: Session = Depends(get_db),
) -> SavingsGoalRead:
    goal = get_or_404(db, goal_id)
    goal.current_amount += payload.amount
    db.commit()
    db.refresh(goal)
    return goal_to_read(goal, bogota_today())


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: int, db: Session = Depends(get_db)) -> Response:
    goal = get_or_404(db, goal_id)
    db.delete(goal)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
