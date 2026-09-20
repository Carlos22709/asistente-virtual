"""Enruta cada mensaje hacia los agentes de dominio seleccionados por el LLM."""

from typing import Any

from sqlalchemy.orm import Session

from ..schemas.assistant import (
    AgentName,
    AssistantChatRequest,
    AssistantChatResponse,
)
from .domain_agents import DomainAgent, FinancialAgent, SecretaryAgent
from .email import EmailService
from .llm import InvalidLLMResponseError, ToolCallingClient


SYSTEM_PROMPT = """Eres el orquestador de un asistente personal móvil.
Debes analizar la solicitud y llamar exactamente una herramienta:
- delegate_to_secretary: tareas, agenda, recordatorios, correos o redacción.
- delegate_to_financial: gastos, ingresos, presupuesto, deudas, ahorro o flujo de caja.
- delegate_to_both: cuando la respuesta requiere información de ambos dominios.
No respondas directamente y no inventes datos. Incluye una razón breve en español."""


def _routing_tool(name: str, description: str) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Razón breve de la selección, en español.",
                    }
                },
                "required": ["reason"],
            },
        },
    }


ROUTING_TOOLS = [
    _routing_tool(
        "delegate_to_secretary",
        "Delega solicitudes de tareas, agenda, recordatorios, correo y redacción.",
    ),
    _routing_tool(
        "delegate_to_financial",
        "Delega solicitudes de gastos, ingresos, presupuestos, deudas y ahorro.",
    ),
    _routing_tool(
        "delegate_to_both",
        "Delega solicitudes que necesitan combinar Secretaría y Finanzas.",
    ),
]

ROUTES = {
    "delegate_to_secretary": [AgentName.secretary],
    "delegate_to_financial": [AgentName.financial],
    "delegate_to_both": [AgentName.secretary, AgentName.financial],
}

class AssistantOrchestrator:
    """Decide que agentes participan y combina sus respuestas."""

    def __init__(
        self,
        client: ToolCallingClient,
        secretary_agent: DomainAgent | None = None,
        financial_agent: DomainAgent | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self.client = client
        self.secretary_agent = secretary_agent or SecretaryAgent(client, email_service)
        self.financial_agent = financial_agent or FinancialAgent(client)

    async def route(
        self, request: AssistantChatRequest, db: Session
    ) -> AssistantChatResponse:
        """Conserva el historial, valida la decision del LLM y ejecuta agentes."""

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(message.model_dump() for message in request.history)
        messages.append({"role": "user", "content": request.message})

        tool_call = await self.client.call_tool(messages, ROUTING_TOOLS)
        agents = ROUTES.get(tool_call.name)
        if agents is None:
            raise InvalidLLMResponseError(
                f"Herramienta de enrutamiento desconocida: {tool_call.name}"
            )

        reason = tool_call.arguments.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise InvalidLLMResponseError("La decisión no incluyó una razón válida")

        executors = {
            AgentName.secretary: self.secretary_agent,
            AgentName.financial: self.financial_agent,
        }
        responses = []
        # El orden declarado por la ruta hace determinista la respuesta combinada.
        for agent in agents:
            responses.append(await executors[agent].respond(db, request))

        return AssistantChatResponse(
            message="\n\n".join(responses),
            agents=agents,
            routing_reason=reason.strip(),
        )
