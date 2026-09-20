"""Crea las tablas del modelo y valida la conectividad con la base configurada."""

from sqlalchemy import inspect, text

from .. import models  # noqa: F401 - registra todos los modelos
from ..config import get_settings
from ..database import Base, engine
from ..services.database_security import secure_supabase_tables


def main() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    Base.metadata.create_all(bind=engine)
    if get_settings().uses_supabase:
        secure_supabase_tables(engine)
    app_tables = sorted(
        table for table in inspect(engine).get_table_names() if table in Base.metadata.tables
    )
    safe_url = engine.url.render_as_string(hide_password=True)
    print(f"Conexión correcta: {safe_url}")
    print(f"Tablas de Kirby disponibles: {', '.join(app_tables)}")
    if get_settings().uses_supabase:
        print("RLS activo y acceso directo de anon/authenticated revocado.")


if __name__ == "__main__":
    main()
