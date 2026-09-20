"""Define el cliente de herramientas y la integracion local con Ollama."""

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class LLMUnavailableError(RuntimeError):
    """El proveedor de lenguaje no se encuentra disponible."""


class InvalidLLMResponseError(RuntimeError):
    """El proveedor respondió sin una llamada de herramienta válida."""


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


class ToolCallingClient(Protocol):
    async def call_tool(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]]
    ) -> ToolCall: ...

    async def complete(self, messages: list[dict[str, str]]) -> str: ...


class OllamaToolCallingClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def _chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, transport=self.transport
            ) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            raise LLMUnavailableError("No fue posible comunicarse con Ollama") from exc

        try:
            result = response.json()
        except ValueError as exc:
            raise InvalidLLMResponseError("Ollama devolvió una respuesta inválida") from exc
        if not isinstance(result, dict):
            raise InvalidLLMResponseError("Ollama devolvió una respuesta inválida")
        return result

    async def call_tool(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]]
    ) -> ToolCall:
        payload = await self._chat(
            {
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "stream": False,
            }
        )
        try:
            tool_calls = payload["message"]["tool_calls"]
            function = tool_calls[0]["function"]
            name = function["name"]
            arguments = function.get("arguments", {})
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise InvalidLLMResponseError(
                "Ollama no seleccionó una herramienta de enrutamiento"
            ) from exc

        if not isinstance(name, str) or not isinstance(arguments, dict):
            raise InvalidLLMResponseError("La llamada de herramienta de Ollama es inválida")
        return ToolCall(name=name, arguments=arguments)

    async def complete(self, messages: list[dict[str, str]]) -> str:
        payload = await self._chat(
            {"model": self.model, "messages": messages, "stream": False}
        )
        try:
            content = payload["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise InvalidLLMResponseError("Ollama no produjo un resumen válido") from exc
        if not isinstance(content, str) or not content.strip():
            raise InvalidLLMResponseError("Ollama no produjo un resumen válido")
        return content.strip()
