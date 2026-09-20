"""Migra los datos de PostgreSQL local hacia una instancia de Supabase."""

from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, func, inspect, select, text

from .. import models  # noqa: F401 - registra todos los modelos
from ..database import Base
from ..services.database_security import secure_supabase_tables


def _database_url(path: Path) -> str:
    value = dotenv_values(path).get("DATABASE_URL")
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"{path.name} no contiene DATABASE_URL")
    return value


def main() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    source = create_engine(
        _database_url(backend_root / ".env.local"), pool_pre_ping=True
    )
    target = create_engine(
        _database_url(backend_root / ".env.supabase"),
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
    )

    try:
        source_tables = set(inspect(source).get_table_names())
        missing = [
            table.name
            for table in Base.metadata.sorted_tables
            if table.name not in source_tables
        ]
        if missing:
            raise RuntimeError(
                "La base local no tiene todas las tablas esperadas: "
                + ", ".join(missing)
            )

        Base.metadata.create_all(bind=target)
        with target.connect() as connection:
            occupied = {
                table.name: connection.scalar(
                    select(func.count()).select_from(table)
                )
                or 0
                for table in Base.metadata.sorted_tables
            }
        non_empty = {name: count for name, count in occupied.items() if count}
        if non_empty:
            details = ", ".join(
                f"{name}={count}" for name, count in non_empty.items()
            )
            raise RuntimeError(
                "Supabase ya contiene datos de Kirby; se canceló para evitar "
                "duplicados: "
                + details
            )

        copied: dict[str, int] = {}
        with source.connect() as source_connection, target.begin() as target_connection:
            for table in Base.metadata.sorted_tables:
                rows = [
                    dict(row)
                    for row in source_connection.execute(select(table)).mappings()
                ]
                if rows:
                    target_connection.execute(table.insert(), rows)
                copied[table.name] = len(rows)

            if target.dialect.name == "postgresql":
                for table in Base.metadata.sorted_tables:
                    if "id" not in table.c:
                        continue
                    table_name = table.name
                    target_connection.execute(
                        text(
                            f'SELECT setval('
                            f"pg_get_serial_sequence(:table_name, 'id'), "
                            f'COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) '
                            f'FROM "{table_name}"'
                        ),
                        {"table_name": table_name},
                    )

        secure_supabase_tables(target)

        print("Migración local a Supabase completada.")
        print("RLS activo y acceso directo de anon/authenticated revocado.")
        for name, count in copied.items():
            print(f"{name}: {count} registros")
    finally:
        source.dispose()
        target.dispose()


if __name__ == "__main__":
    main()
