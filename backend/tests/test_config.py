"""Pruebas de deteccion y seguridad de configuraciones de base de datos."""

import unittest

from pydantic import ValidationError

from app.config import Settings


class SettingsDatabaseTests(unittest.TestCase):
    def test_detects_local_database(self) -> None:
        settings = Settings(
            database_url=(
                "postgresql+psycopg://kirby:secret@localhost:5433/kirby"
            )
        )

        self.assertEqual(settings.database_host, "localhost")
        self.assertTrue(settings.uses_local_database)
        self.assertFalse(settings.uses_supabase)

    def test_detects_supabase_session_pooler(self) -> None:
        settings = Settings(
            database_url=(
                "postgresql+psycopg://postgres.ref:secret@"
                "aws-0-us-east-1.pooler.supabase.com:5432/postgres"
                "?sslmode=require"
            )
        )

        self.assertFalse(settings.uses_local_database)
        self.assertTrue(settings.uses_supabase)

    def test_detects_supabase_direct_connection(self) -> None:
        settings = Settings(
            database_url=(
                "postgresql+psycopg://postgres:secret@"
                "db.project-ref.supabase.co:5432/postgres?sslmode=require"
            )
        )

        self.assertTrue(settings.uses_supabase)

    def test_rejects_supabase_without_ssl(self) -> None:
        with self.assertRaisesRegex(ValidationError, "sslmode=require"):
            Settings(
                database_url=(
                    "postgresql+psycopg://postgres.ref:secret@"
                    "aws-0-us-east-1.pooler.supabase.com:5432/postgres"
                )
            )


if __name__ == "__main__":
    unittest.main()
