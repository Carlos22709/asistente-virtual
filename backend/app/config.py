"""Carga y valida la configuracion del backend desde variables de entorno."""

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    cors_origins: str = "*"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    llm_timeout_seconds: float = Field(default=30, gt=0)
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_max_audio_bytes: int = Field(default=12 * 1024 * 1024, gt=0)
    app_api_token: str | None = Field(default=None, min_length=24)
    bank_webhook_token: str | None = Field(default=None, min_length=24)
    gmail_client_secrets_file: str = "credentials/gmail_client_secret.json"
    gmail_token_file: str = "credentials/gmail_token.json"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("database_url")
    @classmethod
    def require_ssl_for_supabase(cls, value: str) -> str:
        normalized = value.lower()
        is_supabase = ".supabase.com" in normalized or ".supabase.co" in normalized
        if is_supabase and not any(
            sslmode in normalized
            for sslmode in (
                "sslmode=require",
                "sslmode=verify-ca",
                "sslmode=verify-full",
            )
        ):
            raise ValueError(
                "Las conexiones a Supabase deben incluir sslmode=require"
            )
        return value

    @property
    def database_host(self) -> str:
        return urlsplit(self.database_url.replace("postgresql+psycopg", "postgresql", 1)).hostname or ""

    @property
    def uses_local_database(self) -> bool:
        return self.database_host in {"localhost", "127.0.0.1", "::1"}

    @property
    def uses_supabase(self) -> bool:
        return self.database_host.endswith((".supabase.com", ".supabase.co"))

    @property
    def allowed_origins(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
