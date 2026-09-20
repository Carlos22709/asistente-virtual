"""Endpoints CRUD y cambios de estado para tareas."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.enums import TaskPriority, TaskStatus
from ..models.task import Task
from ..schemas.task import (
    TaskComplete,
    TaskCreate,
    TaskRead,
    TaskStatusUpdate,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["Tareas"])


def get_or_404(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task


@router.get("", response_model=list[TaskRead])
def list_tasks(
    completed: bool | None = None,
    task_status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    due_from: datetime | None = None,
    due_to: datetime | None = None,
    db: Session = Depends(get_db),
) -> list[Task]:
    query = select(Task)
    if completed is not None:
        query = query.where(Task.completed == completed)
    if task_status is not None:
        query = query.where(Task.status == task_status)
    if priority is not None:
        query = query.where(Task.priority == priority)
    if due_from is not None:
        query = query.where(Task.due_date >= due_from)
    if due_to is not None:
        query = query.where(Task.due_date <= due_to)
    status_order = case(
        (Task.status == TaskStatus.in_progress, 1),
        (Task.status == TaskStatus.pending, 2),
        else_=3,
    )
    priority_order = case(
        (Task.priority == TaskPriority.high, 1),
        (Task.priority == TaskPriority.medium, 2),
        else_=3,
    )
    return list(
        db.scalars(
            query.order_by(status_order, Task.due_date.asc().nullslast(), priority_order)
        ).all()
    )


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    task = Task(
        **payload.model_dump(),
        completed=payload.status == TaskStatus.completed,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)) -> Task:
    return get_or_404(db, task_id)


@router.put("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)) -> Task:
    task = get_or_404(db, task_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(task, key, value)
    if "status" in changes:
        task.completed = task.status == TaskStatus.completed
    elif "completed" in changes:
        task.status = TaskStatus.completed if task.completed else TaskStatus.pending
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/complete", response_model=TaskRead)
def complete_task(
    task_id: int, payload: TaskComplete, db: Session = Depends(get_db)
) -> Task:
    task = get_or_404(db, task_id)
    task.completed = not task.completed if payload.completed is None else payload.completed
    task.status = TaskStatus.completed if task.completed else TaskStatus.pending
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/status", response_model=TaskRead)
def set_task_status(
    task_id: int, payload: TaskStatusUpdate, db: Session = Depends(get_db)
) -> Task:
    task = get_or_404(db, task_id)
    task.status = payload.status
    task.completed = payload.status == TaskStatus.completed
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)) -> Response:
    task = get_or_404(db, task_id)
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
