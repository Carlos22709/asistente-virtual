"""Argumentos validados de las herramientas de correo del agente secretario."""

from pydantic import BaseModel, Field, field_validator


class EmailListArgs(BaseModel):
    limit: int = Field(default=5, ge=1, le=10)


class EmailSearchArgs(EmailListArgs):
    query: str = Field(min_length=1, max_length=300)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        return value.strip()


class EmailThreadArgs(BaseModel):
    thread_id: str = Field(min_length=1, max_length=200)


class EmailDraftCreateArgs(BaseModel):
    to: str = Field(min_length=3, max_length=320)
    subject: str = Field(min_length=1, max_length=998)
    body: str = Field(min_length=1, max_length=20_000)

    @field_validator("to", "subject", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class EmailDraftSendArgs(BaseModel):
    draft_id: str = Field(min_length=1, max_length=200)
    confirmed: bool = False
