"""Pruebas del enrutador multiagente y del cliente de Ollama."""

import unittest

import httpx

from app.schemas.assistant import AgentName, AssistantChatRequest
from app.services.llm import (
    InvalidLLMResponseError,
    LLMUnavailableError,
    OllamaToolCallingClient,
    ToolCall,
)
from app.services.orchestrator import AssistantOrchestrator, ROUTING_TOOLS


class FakeToolClient:
    def __init__(self, call: ToolCall) -> None:
        self.call = call
        self.messages: list[dict[str, str]] = []
        self.tools: list[dict] = []

    async def call_tool(self, messages: list[dict[str, str]], tools: list[dict]) -> ToolCall:
        self.messages = messages
        self.tools = tools
        return self.call


class FakeDomainAgent:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[object, AssistantChatRequest]] = []

    async def respond(self, db: object, request: AssistantChatRequest) -> str:
        self.calls.append((db, request))
        return self.response


class AssistantOrchestratorTest(unittest.IsolatedAsyncioTestCase):
    async def test_routes_to_each_supported_agent_combination(self) -> None:
        cases = [
            ("delegate_to_secretary", [AgentName.secretary]),
            ("delegate_to_financial", [AgentName.financial]),
            ("delegate_to_both", [AgentName.secretary, AgentName.financial]),
        ]

        for tool_name, expected_agents in cases:
            with self.subTest(tool_name=tool_name):
                client = FakeToolClient(ToolCall(tool_name, {"reason": "Prueba de ruta"}))
                secretary = FakeDomainAgent("Respuesta de Secretaría")
                financial = FakeDomainAgent("Respuesta de Finanzas")
                orchestrator = AssistantOrchestrator(client, secretary, financial)
                db = object()

                result = await orchestrator.route(
                    AssistantChatRequest(message="Ayúdame con esta solicitud"), db
                )

                self.assertEqual(result.agents, expected_agents)
                self.assertEqual(result.routing_reason, "Prueba de ruta")
                self.assertEqual(result.status, "completed")
                self.assertEqual(client.messages[-1]["role"], "user")
                self.assertEqual(client.tools, ROUTING_TOOLS)
                self.assertEqual(len(secretary.calls), int(AgentName.secretary in expected_agents))
                self.assertEqual(len(financial.calls), int(AgentName.financial in expected_agents))
                expected_messages = []
                if AgentName.secretary in expected_agents:
                    expected_messages.append("Respuesta de Secretaría")
                if AgentName.financial in expected_agents:
                    expected_messages.append("Respuesta de Finanzas")
                self.assertEqual(result.message, "\n\n".join(expected_messages))

    async def test_preserves_conversation_history(self) -> None:
        client = FakeToolClient(
            ToolCall("delegate_to_secretary", {"reason": "Es una tarea"})
        )
        orchestrator = AssistantOrchestrator(
            client, FakeDomainAgent("Secretaría"), FakeDomainAgent("Finanzas")
        )

        await orchestrator.route(
            AssistantChatRequest(
                message="¿Y para mañana?",
                history=[
                    {"role": "user", "content": "Revisa mis tareas"},
                    {"role": "assistant", "content": "Claro"},
                ],
            ),
            object(),
        )

        self.assertEqual([item["role"] for item in client.messages], [
            "system",
            "user",
            "assistant",
            "user",
        ])

    async def test_rejects_an_unknown_tool(self) -> None:
        orchestrator = AssistantOrchestrator(
            FakeToolClient(ToolCall("unknown", {"reason": "No válida"}))
        )

        with self.assertRaises(InvalidLLMResponseError):
            await orchestrator.route(AssistantChatRequest(message="Haz algo"), object())

    async def test_rejects_a_decision_without_reason(self) -> None:
        orchestrator = AssistantOrchestrator(
            FakeToolClient(ToolCall("delegate_to_secretary", {}))
        )

        with self.assertRaises(InvalidLLMResponseError):
            await orchestrator.route(
                AssistantChatRequest(message="Revisa mi agenda"), object()
            )


class OllamaToolCallingClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_parses_an_ollama_tool_call(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/chat")
            return httpx.Response(
                200,
                json={
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "delegate_to_financial",
                                    "arguments": {"reason": "Consulta de presupuesto"},
                                }
                            }
                        ]
                    }
                },
            )

        client = OllamaToolCallingClient(
            "http://ollama.test",
            "llama3.2",
            5,
            transport=httpx.MockTransport(handler),
        )

        result = await client.call_tool(
            [{"role": "user", "content": "¿Cuánto dinero me queda?"}],
            ROUTING_TOOLS,
        )

        self.assertEqual(result.name, "delegate_to_financial")
        self.assertEqual(result.arguments["reason"], "Consulta de presupuesto")

    async def test_reports_an_unavailable_ollama_server(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"error": "offline"})

        client = OllamaToolCallingClient(
            "http://ollama.test",
            "llama3.2",
            5,
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(LLMUnavailableError):
            await client.call_tool(
                [{"role": "user", "content": "Revisa mi agenda"}],
                ROUTING_TOOLS,
            )

    async def test_parses_a_plain_ollama_completion(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"message": {"content": "Resumen listo"}})

        client = OllamaToolCallingClient(
            "http://ollama.test",
            "llama3.2",
            5,
            transport=httpx.MockTransport(handler),
        )

        result = await client.complete(
            [{"role": "user", "content": "Resume este hilo"}]
        )

        self.assertEqual(result, "Resumen listo")
