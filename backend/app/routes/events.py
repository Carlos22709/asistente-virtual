"""Endpoints CRUD para los eventos de agenda."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.event import Event
from ..schemas.event import EventCreate, EventRead, EventUpdate
from ..services.clock import bogota_now

router = APIRouter(prefix="/events", tags=["Agenda"])


def get_or_404(db: Session, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return event


@router.get("", response_model=list[EventRead])
def list_events(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    upcoming: bool = False,
    db: Session = Depends(get_db),
) -> list[Event]:
    query = select(Event)
    if upcoming:
        query = query.where(Event.start_datetime >= bogota_now())
    if date_from is not None:
        query = query.where(Event.start_datetime >= date_from)
    if date_to is not None:
        query = query.where(Event.start_datetime <= date_to)
    return list(db.scalars(query.order_by(Event.start_datetime)).all())


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Session = Depends(get_db)) -> Event:
    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: int, db: Session = Depends(get_db)) -> Event:
    return get_or_404(db, event_id)


@router.put("/{event_id}", response_model=EventRead)
def update_event(event_id: int, payload: EventUpdate, db: Session = Depends(get_db)) -> Event:
    event = get_or_404(db, event_id)
    for key, value in payload.model_dump().items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: Session = Depends(get_db)) -> Response:
    event = get_or_404(db, event_id)
    db.delete(event)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
