"""Contratos y reglas de validacion para eventos de agenda."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..services.clock import BOGOTA


class EventBase(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    start_datetime: datetime
    end_datetime: datetime | None = None
    location: str | None = Field(default=None, max_length=240)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El título no puede estar vacío")
        return value.strip()

    @field_validator("start_datetime", "end_datetime")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        return value.replace(tzinfo=BOGOTA) if value is not None and value.tzinfo is None else value

    @model_validator(mode="after")
    def validate_dates(self) -> "EventBase":
        if self.end_datetime and self.end_datetime < self.start_datetime:
            raise ValueError("La fecha final no puede ser anterior a la inicial")
        return self


class EventCreate(EventBase):
    pass


class EventUpdate(EventBase):
    pass


class EventRead(EventBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
