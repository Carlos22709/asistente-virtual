"""Pruebas de comandos y salvaguardas de los agentes de dominio."""

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models.budget import Budget
from app.models.enums import (
    ExpenseCategory,
    FinancialAccountType,
    IncomeCategory,
    TaskPriority,
    TaskStatus,
)
from app.models.event import Event
from app.models.expense import Expense
from app.models.financial_account import FinancialAccount
from app.models.income import Income
from app.models.recurring_transaction import RecurringTransaction
from app.models.savings_goal import SavingsGoal
from app.models.task import Task
from app.schemas.assistant import AssistantChatRequest
from app.services.clock import bogota_now
from app.services.domain_agents import FinancialAgent, SecretaryAgent
from app.services.email import MailDraft, MailMessage, SentMail
from app.services.llm import ToolCall


class StaticToolClient:
    def __init__(self, call: ToolCall, completion: str = "Resumen de prueba") -> None:
        self.call = call
        self.completion = completion
        self.completion_messages: list[dict[str, str]] = []

    async def call_tool(self, messages: list[dict], tools: list[dict]) -> ToolCall:
        return self.call

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.completion_messages = messages
        return self.completion


class FakeEmailService:
    def __init__(self) -> None:
        self.sent_drafts: list[str] = []
        self.created_drafts: list[tuple[str, str, str]] = []
        self.messages = [
            MailMessage(
                id="message-1",
                thread_id="thread-1",
                sender="Ana <ana@example.com>",
                subject="Estado del proyecto",
                received_at=datetime(2026, 9, 17, 14, 0, tzinfo=timezone.utc),
                snippet="Ya está listo el informe.",
                body="El informe ya está listo. Falta aprobarlo.",
            )
        ]

    def list_unread(self, limit: int = 5) -> list[MailMessage]:
        return self.messages[:limit]

    def search(self, query: str, limit: int = 5) -> list[MailMessage]:
        return self.messages[:limit]

    def get_thread(self, thread_id: str) -> list[MailMessage]:
        return self.messages if thread_id == "thread-1" else []

    def create_draft(self, to: str, subject: str, body: str) -> MailDraft:
        self.created_drafts.append((to, subject, body))
        return MailDraft(id="draft-1", to=to, subject=subject)

    def send_draft(self, draft_id: str) -> SentMail:
        self.sent_drafts.append(draft_id)
        return SentMail(id="sent-1", thread_id="thread-2")


class DomainAgentsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    async def test_secretary_reads_pending_tasks_and_upcoming_events(self) -> None:
        now = bogota_now()
        self.db.add_all(
            [
                Task(
                    title="Entregar informe",
                    due_date=now + timedelta(days=1),
                    priority=TaskPriority.high,
                ),
                Task(
                    title="Tarea terminada",
                    completed=True,
                    status=TaskStatus.completed,
                ),
                Event(title="Clase de redes", start_datetime=now + timedelta(days=2)),
            ]
        )
        self.db.commit()

        agent = SecretaryAgent(StaticToolClient(ToolCall("get_secretary_overview", {})))
        response = await agent.respond(
            self.db, AssistantChatRequest(message="¿Qué tengo pendiente?")
        )

        self.assertIn("Entregar informe", response)
        self.assertIn("Clase de redes", response)
        self.assertNotIn("Tarea terminada", response)

    async def test_financial_reads_expenses_and_current_budget(self) -> None:
        today = bogota_now().date()
        self.db.add_all(
            [
                Expense(
                    description="Almuerzo",
                    amount=Decimal("25000.00"),
                    category=ExpenseCategory.food,
                    date=today,
                ),
                Budget(month=today.month, year=today.year, amount=Decimal("100000.00")),
            ]
        )
        self.db.commit()

        agent = FinancialAgent(StaticToolClient(ToolCall("get_financial_overview", {})))
        response = await agent.respond(
            self.db, AssistantChatRequest(message="¿Cuánto dinero me queda?")
        )

        self.assertIn("$25.000,00", response)
        self.assertIn("$75.000,00 disponible", response)
        self.assertIn("Almuerzo", response)

    async def test_secretary_creates_a_task(self) -> None:
        due_date = bogota_now() + timedelta(days=1)
        agent = SecretaryAgent(
            StaticToolClient(
                ToolCall(
                    "create_task",
                    {
                        "title": "Preparar exposición",
                        "due_date": due_date.isoformat(),
                        "priority": "Alta",
                    },
                )
            )
        )

        response = await agent.respond(
            self.db, AssistantChatRequest(message="Crea una tarea para mañana")
        )

        task = self.db.scalar(select(Task).where(Task.title == "Preparar exposición"))
        self.assertIsNotNone(task)
        self.assertEqual(task.priority, TaskPriority.high)
        self.assertIn("creó la tarea", response)

    async def test_secretary_creates_an_event(self) -> None:
        start = bogota_now() + timedelta(days=2)
        agent = SecretaryAgent(
            StaticToolClient(
                ToolCall(
                    "create_event",
                    {
                        "title": "Reunión de proyecto",
                        "start_datetime": start.isoformat(),
                        "location": "Biblioteca",
                    },
                )
            )
        )

        response = await agent.respond(
            self.db, AssistantChatRequest(message="Agenda una reunión")
        )

        event = self.db.scalar(select(Event).where(Event.title == "Reunión de proyecto"))
        self.assertIsNotNone(event)
        self.assertEqual(event.location, "Biblioteca")
        self.assertIn("agregó", response)

    async def test_secretary_changes_task_to_in_progress(self) -> None:
        self.db.add(Task(title="Preparar demostración"))
        self.db.commit()
        agent = SecretaryAgent(
            StaticToolClient(
                ToolCall(
                    "update_task_status",
                    {"title": "Preparar demostración", "status": "En progreso"},
                )
            )
        )

        response = await agent.respond(
            self.db,
            AssistantChatRequest(message="Empieza la tarea de la demostración"),
        )

        task = self.db.scalar(
            select(Task).where(Task.title == "Preparar demostración")
        )
        self.assertEqual(task.status, TaskStatus.in_progress)
        self.assertFalse(task.completed)
        self.assertIn("En progreso", response)

    async def test_financial_records_an_expense(self) -> None:
        today = bogota_now().date()
        agent = FinancialAgent(
            StaticToolClient(
                ToolCall(
                    "record_expense",
                    {
                        "description": "Pasaje de bus",
                        "amount": 3500,
                        "category": "Transporte",
                        "date": today.isoformat(),
                    },
                )
            )
        )

        response = await agent.respond(
            self.db, AssistantChatRequest(message="Gasté 3500 en el bus")
        )

        expense = self.db.scalar(select(Expense).where(Expense.description == "Pasaje de bus"))
        self.assertIsNotNone(expense)
        self.assertEqual(expense.amount, Decimal("3500.00"))
        self.assertIn("registró $3.500,00", response)

    async def test_financial_records_an_income_and_updates_cash_flow(self) -> None:
        today = bogota_now().date()
        self.db.add(
            Expense(
                description="Transporte",
                amount=Decimal("20000.00"),
                category=ExpenseCategory.transport,
                date=today,
            )
        )
        self.db.commit()
        agent = FinancialAgent(
            StaticToolClient(
                ToolCall(
                    "record_income",
                    {
                        "description": "Pago de monitoría",
                        "amount": 150000,
                        "category": "Trabajo independiente",
                        "date": today.isoformat(),
                    },
                )
            )
        )

        response = await agent.respond(
            self.db, AssistantChatRequest(message="Recibí 150 mil por la monitoría")
        )

        income = self.db.scalar(
            select(Income).where(Income.description == "Pago de monitoría")
        )
        self.assertIsNotNone(income)
        self.assertEqual(income.category, IncomeCategory.freelance)
        self.assertIn("$150.000,00", response)
        self.assertIn("$130.000,00", response)

    async def test_financial_creates_a_recurring_expense(self) -> None:
        today = bogota_now().date()
        agent = FinancialAgent(
            StaticToolClient(
                ToolCall(
                    "create_recurring_transaction",
                    {
                        "description": "Arriendo",
                        "amount": 700000,
                        "kind": "Gasto",
                        "category": "Otros",
                        "frequency": "Mensual",
                        "start_date": today.isoformat(),
                    },
                )
            )
        )

        response = await agent.respond(
            self.db,
            AssistantChatRequest(
                message="Cada mes pago 700 mil de arriendo desde hoy"
            ),
        )

        item = self.db.scalar(select(RecurringTransaction))
        self.assertIsNotNone(item)
        self.assertEqual(item.description, "Arriendo")
        self.assertEqual(item.amount, Decimal("700000.00"))
        self.assertIn("frecuencia mensual", response)

    async def test_financial_records_a_credit_card_with_calculations(self) -> None:
        agent = FinancialAgent(
            StaticToolClient(
                ToolCall(
                    "create_financial_account",
                    {
                        "name": "Tarjeta universitaria",
                        "account_type": "Tarjeta de crédito",
                        "balance": 400000,
                        "credit_limit": 2000000,
                        "annual_interest_rate": 24,
                        "statement_day": 15,
                        "payment_due_day": 30,
                        "minimum_payment": 50000,
                    },
                )
            )
        )

        response = await agent.respond(
            self.db,
            AssistantChatRequest(message="Registra mi tarjeta universitaria"),
        )

        account = self.db.scalar(
            select(FinancialAccount).where(
                FinancialAccount.name == "Tarjeta universitaria"
            )
        )
        self.assertIsNotNone(account)
        self.assertEqual(account.account_type, FinancialAccountType.credit_card)
        self.assertIn("$1.600.000,00", response)
        self.assertIn("$8.000,00", response)

    async def test_financial_requests_missing_account_details(self) -> None:
        agent = FinancialAgent(
            StaticToolClient(
                ToolCall(
                    "request_financial_account_details",
                    {"missing_fields": ["saldo adeudado", "día de pago"]},
                )
            )
        )

        response = await agent.respond(
            self.db,
            AssistantChatRequest(message="Registra mi préstamo"),
        )

        self.assertIn("saldo adeudado", response)
        self.assertIn("día de pago", response)

    async def test_financial_creates_a_savings_goal(self) -> None:
        target_date = bogota_now().date() + timedelta(days=90)
        agent = FinancialAgent(
            StaticToolClient(
                ToolCall(
                    "create_savings_goal",
                    {
                        "name": "Fondo de emergencia",
                        "target_amount": 1000000,
                        "current_amount": 100000,
                        "target_date": target_date.isoformat(),
                    },
                )
            )
        )

        response = await agent.respond(
            self.db,
            AssistantChatRequest(message="Crea una meta de un millón"),
        )

        goal = self.db.scalar(
            select(SavingsGoal).where(SavingsGoal.name == "Fondo de emergencia")
        )
        self.assertIsNotNone(goal)
        self.assertIn("10.0%", response)

    async def test_financial_adds_a_savings_contribution(self) -> None:
        self.db.add(
            SavingsGoal(
                name="Viaje académico",
                target_amount=Decimal("500000.00"),
                current_amount=Decimal("100000.00"),
            )
        )
        self.db.commit()
        agent = FinancialAgent(
            StaticToolClient(
                ToolCall(
                    "contribute_to_savings_goal",
                    {"name": "viaje académico", "amount": 50000},
                )
            )
        )

        response = await agent.respond(
            self.db,
            AssistantChatRequest(message="Agrega 50 mil a mi viaje académico"),
        )

        goal = self.db.scalar(
            select(SavingsGoal).where(SavingsGoal.name == "Viaje académico")
        )
        self.assertEqual(goal.current_amount, Decimal("150000.00"))
        self.assertIn("30.0%", response)

    async def test_secretary_lists_unread_email(self) -> None:
        email_service = FakeEmailService()
        agent = SecretaryAgent(
            StaticToolClient(ToolCall("list_unread_emails", {"limit": 5})),
            email_service,
        )

        response = await agent.respond(
            self.db, AssistantChatRequest(message="¿Qué correos tengo sin leer?")
        )

        self.assertIn("Estado del proyecto", response)
        self.assertIn("thread-1", response)

    async def test_secretary_prioritizes_unread_email_safely(self) -> None:
        email_service = FakeEmailService()
        client = StaticToolClient(
            ToolCall("prioritize_unread_emails", {"limit": 5}),
            completion=(
                "Alta: Estado del proyecto, Ana. Acción: aprobar el informe. "
                "Hilo: thread-1."
            ),
        )
        agent = SecretaryAgent(client, email_service)

        response = await agent.respond(
            self.db,
            AssistantChatRequest(message="Prioriza mis correos urgentes"),
        )

        self.assertIn("Priorización", response)
        self.assertIn("thread-1", response)
        self.assertIn("no confiable", client.completion_messages[0]["content"])
        self.assertIn("<correo", client.completion_messages[1]["content"])

    async def test_secretary_summarizes_an_email_thread_with_llm(self) -> None:
        email_service = FakeEmailService()
        agent = SecretaryAgent(
            StaticToolClient(
                ToolCall("summarize_email_thread", {"thread_id": "thread-1"}),
                completion="El informe está listo y falta aprobarlo.",
            ),
            email_service,
        )

        response = await agent.respond(
            self.db, AssistantChatRequest(message="Resume ese hilo")
        )

        self.assertIn("falta aprobarlo", response)

    async def test_secretary_creates_email_draft_without_sending(self) -> None:
        email_service = FakeEmailService()
        agent = SecretaryAgent(
            StaticToolClient(
                ToolCall(
                    "create_email_draft",
                    {
                        "to": "ana@example.com",
                        "subject": "Re: Estado del proyecto",
                        "body": "Gracias, lo revisaré hoy.",
                    },
                )
            ),
            email_service,
        )

        response = await agent.respond(
            self.db, AssistantChatRequest(message="Prepara una respuesta")
        )

        self.assertEqual(len(email_service.created_drafts), 1)
        self.assertEqual(email_service.sent_drafts, [])
        self.assertIn("No se ha enviado", response)
        self.assertIn("draft-1", response)

    async def test_secretary_does_not_send_email_without_confirmation(self) -> None:
        email_service = FakeEmailService()
        agent = SecretaryAgent(
            StaticToolClient(
                ToolCall(
                    "send_email_draft",
                    {"draft_id": "draft-1", "confirmed": False},
                )
            ),
            email_service,
        )

        response = await agent.respond(
            self.db, AssistantChatRequest(message="Muéstrame el borrador")
        )

        self.assertEqual(email_service.sent_drafts, [])
        self.assertIn("no se envió", response)

    async def test_secretary_sends_email_after_explicit_confirmation(self) -> None:
        email_service = FakeEmailService()
        agent = SecretaryAgent(
            StaticToolClient(
                ToolCall(
                    "send_email_draft",
                    {"draft_id": "draft-1", "confirmed": True},
                )
            ),
            email_service,
        )

        response = await agent.respond(
            self.db,
            AssistantChatRequest(
                message="Sí, envía el borrador",
                history=[
                    {
                        "role": "assistant",
                        "content": "Creé el borrador. Identificador: draft-1.",
                    }
                ],
            ),
        )

        self.assertEqual(email_service.sent_drafts, ["draft-1"])
        self.assertIn("envió el borrador", response)

    async def test_secretary_rejects_model_confirmation_without_user_confirmation(self) -> None:
        email_service = FakeEmailService()
        agent = SecretaryAgent(
            StaticToolClient(
                ToolCall(
                    "send_email_draft",
                    {"draft_id": "draft-1", "confirmed": True},
                )
            ),
            email_service,
        )

        response = await agent.respond(
            self.db,
            AssistantChatRequest(
                message="Muéstrame el borrador",
                history=[
                    {
                        "role": "assistant",
                        "content": "Creé el borrador. Identificador: draft-1.",
                    }
                ],
            ),
        )

        self.assertEqual(email_service.sent_drafts, [])
        self.assertIn("no se envió", response)


if __name__ == "__main__":
    unittest.main()
