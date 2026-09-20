"""Configura SQLAlchemy y expone sesiones transaccionales para FastAPI."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
database_url = settings.database_url
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine_options: dict[str, object] = {
    "pool_pre_ping": True,
    "connect_args": connect_args,
}
if settings.uses_supabase:
    engine_options.update(pool_size=5, max_overflow=5, pool_recycle=300)
engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
