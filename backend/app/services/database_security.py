"""Aplica privilegios minimos a las tablas cuando se utiliza Supabase."""

from sqlalchemy import Engine, text

from ..database import Base


def secure_supabase_tables(engine: Engine) -> None:
    """Impide el acceso directo a las tablas desde los roles de la Data API."""
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            quoted_name = '"' + table.name.replace('"', '""') + '"'
            connection.execute(
                text(f"ALTER TABLE public.{quoted_name} ENABLE ROW LEVEL SECURITY")
            )
            connection.execute(
                text(
                    f"REVOKE ALL ON TABLE public.{quoted_name} "
                    "FROM anon, authenticated"
                )
            )
