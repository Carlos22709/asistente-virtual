"""Contratos y normalizacion de tareas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.enums import TaskPriority, TaskStatus
from ..services.clock import BOGOTA


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    due_date: datetime | None = None
    priority: TaskPriority = TaskPriority.medium
    status: TaskStatus = TaskStatus.pending

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El título no puede estar vacío")
        return value.strip()

    @field_validator("due_date")
    @classmethod
    def normalize_due_date(cls, value: datetime | None) -> datetime | None:
        return value.replace(tzinfo=BOGOTA) if value is not None and value.tzinfo is None else value


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    due_date: datetime | None = None
    priority: TaskPriority | None = None
    completed: bool | None = None
    status: TaskStatus | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("El título no puede estar vacío")
        return value.strip() if value else value

    @field_validator("due_date")
    @classmethod
    def normalize_due_date(cls, value: datetime | None) -> datetime | None:
        return value.replace(tzinfo=BOGOTA) if value is not None and value.tzinfo is None else value


class TaskRead(TaskBase):
    id: int
    completed: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TaskComplete(BaseModel):
    completed: bool | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
