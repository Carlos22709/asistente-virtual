"""Centraliza fechas y horas en la zona horaria de Bogota."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")


def bogota_now() -> datetime:
    return datetime.now(BOGOTA)


def bogota_today() -> date:
    return bogota_now().date()
