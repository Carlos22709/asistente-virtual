"""Contratos de conversacion, enrutamiento y transcripcion del asistente."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AgentName(str, Enum):
    secretary = "secretary"
    financial = "financial"


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El mensaje no puede estar vacío")
        return value.strip()


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ConversationMessage] = Field(default_factory=list, max_length=20)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El mensaje no puede estar vacío")
        return value.strip()


class AssistantChatResponse(BaseModel):
    message: str
    agents: list[AgentName] = Field(min_length=1)
    routing_reason: str
    status: Literal["completed"] = "completed"


class AssistantTranscriptionResponse(BaseModel):
    text: str
    language: str
