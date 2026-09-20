"""Contratos del diagnostico, respaldo y restauracion del sistema."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class ComponentStatus(BaseModel):
    status: str
    detail: str


class SystemStatus(BaseModel):
    status: str
    checked_at: datetime
    database_provider: str
    api_auth_enabled: bool
    components: dict[str, ComponentStatus]


class BackupDocument(BaseModel):
    version: Literal[1] = 1
    exported_at: datetime
    tables: dict[str, list[dict[str, Any]]]


class BackupRestoreRequest(BaseModel):
    backup: BackupDocument
    replace_existing: bool = False


class BackupRestoreResult(BaseModel):
    status: str
    restored_rows: int
    tables: dict[str, int]
