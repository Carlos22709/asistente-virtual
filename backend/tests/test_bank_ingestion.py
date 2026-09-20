"""Pruebas de extraccion, rechazo y deduplicacion de alertas bancarias."""

import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models.expense import Expense
from app.schemas.bank_webhook import BankTransactionExtraction, BankWebhookRequest
from app.services.bank_ingestion import BankNotificationParser, ingest_extraction
from app.services.llm import InvalidLLMResponseError, ToolCall


class StaticToolClient:
    def __init__(self, call: ToolCall) -> None:
        self.call = call

    async def call_tool(self, messages: list[dict], tools: list[dict]) -> ToolCall:
        return self.call


class BankNotificationParserTest(unittest.IsolatedAsyncioTestCase):
    async def test_parses_a_structured_transaction(self) -> None:
        parser = BankNotificationParser(
            StaticToolClient(
                ToolCall(
                    "extract_bank_transaction",
                    {
                        "is_transaction": True,
                        "amount": 25900,
                        "currency": "cop",
                        "merchant": "Tienda Central",
                        "transaction_date": "2026-09-16",
                        "category": "Compras",
                        "payment_method": "Tarjeta 1234",
                        "reason": "Compra aprobada",
                    },
                )
            )
        )

        result = await parser.parse("Compra aprobada por $25.900 en Tienda Central")

        self.assertTrue(result.is_transaction)
        self.assertEqual(result.currency, "COP")
        self.assertEqual(result.merchant, "Tienda Central")

    async def test_rejects_an_incomplete_transaction(self) -> None:
        parser = BankNotificationParser(
            StaticToolClient(
                ToolCall(
                    "extract_bank_transaction",
                    {"is_transaction": True, "amount": 10000, "reason": "Incompleta"},
                )
            )
        )

        with self.assertRaises(InvalidLLMResponseError):
            await parser.parse("Compra sin datos suficientes")

    async def test_supplies_a_reason_when_ollama_returns_it_empty(self) -> None:
        parser = BankNotificationParser(
            StaticToolClient(
                ToolCall(
                    "extract_bank_transaction",
                    {
                        "is_transaction": True,
                        "amount": 45900,
                        "currency": "COP",
                        "merchant": "Mercado Campus",
                        "transaction_date": "2026-09-16",
                        "category": "Compras",
                        "reason": "",
                    },
                )
            )
        )

        result = await parser.parse("Compra aprobada por 45900 COP en Mercado Campus")

        self.assertEqual(result.reason, "Transacción identificada en la notificación.")

    async def test_recovers_an_explicit_approved_transaction(self) -> None:
        parser = BankNotificationParser(
            StaticToolClient(
                ToolCall(
                    "extract_bank_transaction",
                    {
                        "is_transaction": False,
                        "amount": 45900,
                        "currency": "COP",
                        "merchant": "Mercado Campus",
                        "transaction_date": "2026-09-16",
                        "category": "Compras",
                        "reason": "",
                    },
                )
            )
        )

        result = await parser.parse("Compra aprobada por 45900 COP en Mercado Campus")

        self.assertTrue(result.is_transaction)

    async def test_keeps_a_rejected_payment_ignored(self) -> None:
        parser = BankNotificationParser(
            StaticToolClient(
                ToolCall(
                    "extract_bank_transaction",
                    {
                        "is_transaction": True,
                        "amount": 45900,
                        "currency": "COP",
                        "merchant": "Mercado Campus",
                        "transaction_date": "2026-09-16",
                        "category": "Compras",
                        "reason": "Pago detectado",
                    },
                )
            )
        )

        result = await parser.parse("Compra rechazada por 45900 COP en Mercado Campus")

        self.assertFalse(result.is_transaction)


class BankIngestionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_ignores_non_transaction_notifications(self) -> None:
        payload = BankWebhookRequest(
            text="Nunca compartas este código de verificación con otra persona.",
            source="test",
        )
        extraction = BankTransactionExtraction(
            is_transaction=False,
            reason="Es un código de verificación",
        )

        result = ingest_extraction(self.db, payload, extraction)

        self.assertEqual(result.status, "ignored")
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Expense)), 0)

    def test_ignores_foreign_currency_without_conversion(self) -> None:
        payload = BankWebhookRequest(
            text="Compra aprobada por 20 USD en Example Store.", source="test"
        )
        extraction = BankTransactionExtraction(
            is_transaction=True,
            amount="20.00",
            currency="USD",
            merchant="Example Store",
            transaction_date="2026-09-16",
            category="Compras",
            reason="Compra en dólares",
        )

        result = ingest_extraction(self.db, payload, extraction)

        self.assertEqual(result.status, "ignored")
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Expense)), 0)


if __name__ == "__main__":
    unittest.main()
