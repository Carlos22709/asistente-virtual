"""Pruebas integrales de rutas, persistencia y agentes sobre una base temporal."""

import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

temporary_directory = tempfile.TemporaryDirectory()
database_path = Path(temporary_directory.name) / "kirby_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
os.environ["BANK_WEBHOOK_TOKEN"] = "test-webhook-token-with-32-characters"

from app.main import app  # noqa: E402
from app.database import engine  # noqa: E402
from app.routes.assistant import get_orchestrator  # noqa: E402
from app.routes.webhooks import get_bank_parser  # noqa: E402
from app.schemas.bank_webhook import BankTransactionExtraction  # noqa: E402
from app.services.clock import bogota_now  # noqa: E402
from app.services.llm import ToolCall  # noqa: E402
from app.services.orchestrator import AssistantOrchestrator  # noqa: E402


class BothAgentsClient:
    async def call_tool(self, messages: list[dict], tools: list[dict]) -> ToolCall:
        names = {tool["function"]["name"] for tool in tools}
        if "delegate_to_both" in names:
            return ToolCall("delegate_to_both", {"reason": "Consulta combinada"})
        if "get_secretary_overview" in names:
            return ToolCall("get_secretary_overview", {})
        if "get_financial_overview" in names:
            return ToolCall("get_financial_overview", {})
        raise AssertionError(f"Conjunto de herramientas inesperado: {names}")


class FakeBankParser:
    async def parse(self, text: str) -> BankTransactionExtraction:
        return BankTransactionExtraction(
            is_transaction=True,
            amount="45900.00",
            currency="COP",
            merchant="Mercado Campus",
            transaction_date=bogota_now().date(),
            category="Comida",
            payment_method="Tarjeta terminada en 1234",
            external_reference="ABC123",
            reason="Compra aprobada",
        )


class ApiEndToEndTest(unittest.TestCase):
    def test_main_flows_and_persistence(self) -> None:
        now = bogota_now()
        today = now.date().isoformat()
        future = (now + timedelta(days=2)).isoformat()
        later = (now + timedelta(days=2, hours=1)).isoformat()
        savings_date = (now + timedelta(days=90)).date().isoformat()

        with TestClient(app) as client:
            self.assertEqual(client.get("/health").status_code, 200)
            self.assertEqual(client.get("/docs").status_code, 200)

            invalid_task = client.post("/tasks", json={"title": "   ", "priority": "Media"})
            self.assertEqual(invalid_task.status_code, 422)

            task = client.post(
                "/tasks",
                json={"title": "Entregar proyecto", "priority": "Alta", "due_date": future},
            )
            self.assertEqual(task.status_code, 201)
            task_id = task.json()["id"]
            self.assertEqual(len(client.get("/tasks").json()), 1)
            updated_task = client.put(
                f"/tasks/{task_id}",
                json={"title": "Entregar proyecto final", "priority": "Alta"},
            )
            self.assertEqual(updated_task.status_code, 200)
            in_progress = client.patch(
                f"/tasks/{task_id}/status", json={"status": "En progreso"}
            )
            self.assertEqual(in_progress.status_code, 200)
            self.assertEqual(in_progress.json()["status"], "En progreso")
            self.assertFalse(in_progress.json()["completed"])
            self.assertEqual(len(client.get("/tasks?task_status=En%20progreso").json()), 1)
            completed = client.patch(
                f"/tasks/{task_id}/complete", json={"completed": True}
            )
            self.assertTrue(completed.json()["completed"])
            self.assertEqual(completed.json()["status"], "Completada")
            self.assertEqual(client.get("/tasks/99999").status_code, 404)

            invalid_expense = client.post(
                "/expenses",
                json={"description": "Nada", "amount": "0", "category": "Otros", "date": today},
            )
            self.assertEqual(invalid_expense.status_code, 422)
            expense = client.post(
                "/expenses",
                json={"description": "Almuerzo", "amount": "25000.00", "category": "Comida", "date": today},
            )
            self.assertEqual(expense.status_code, 201)
            expense_id = expense.json()["id"]
            updated_expense = client.put(
                f"/expenses/{expense_id}",
                json={"description": "Almuerzo universidad", "amount": "27000.00", "category": "Universidad", "date": today, "note": "Menú del día"},
            )
            self.assertEqual(updated_expense.status_code, 200)
            summary = client.get("/expenses/summary")
            self.assertEqual(summary.status_code, 200)
            self.assertEqual(float(summary.json()["today"]), 27000.0)

            invalid_income = client.post(
                "/incomes",
                json={"description": "Nada", "amount": "0", "category": "Otros", "date": today},
            )
            self.assertEqual(invalid_income.status_code, 422)
            income = client.post(
                "/incomes",
                json={"description": "Pago de monitoría", "amount": "800000.00", "category": "Trabajo independiente", "date": today},
            )
            self.assertEqual(income.status_code, 201)
            income_id = income.json()["id"]
            updated_income = client.put(
                f"/incomes/{income_id}",
                json={"description": "Pago monitoría universidad", "amount": "810000.00", "category": "Trabajo independiente", "date": today, "note": "Septiembre"},
            )
            self.assertEqual(updated_income.status_code, 200)
            cash_flow = client.get("/incomes/cash-flow")
            self.assertEqual(cash_flow.status_code, 200)
            self.assertEqual(float(cash_flow.json()["income_month"]), 810000.0)
            self.assertEqual(float(cash_flow.json()["expenses_month"]), 27000.0)
            self.assertEqual(float(cash_flow.json()["net_month"]), 783000.0)

            recurring = client.post(
                "/finances/recurring",
                json={
                    "description": "Arriendo mensual",
                    "amount": "650000.00",
                    "kind": "Gasto",
                    "category": "Otros",
                    "frequency": "Mensual",
                    "interval": 1,
                    "start_date": today,
                    "active": True,
                },
            )
            self.assertEqual(recurring.status_code, 201)
            recurring_id = recurring.json()["id"]
            self.assertEqual(len(client.get("/finances/recurring").json()), 1)
            forecast = client.get("/finances/forecast?months=3")
            self.assertEqual(forecast.status_code, 200)
            self.assertEqual(len(forecast.json()["points"]), 3)

            invalid_card = client.post(
                "/financial-accounts",
                json={
                    "name": "Tarjeta incompleta",
                    "account_type": "Tarjeta de crédito",
                    "balance": "100000.00",
                    "payment_due_day": 20,
                },
            )
            self.assertEqual(invalid_card.status_code, 422)
            card = client.post(
                "/financial-accounts",
                json={
                    "name": "Tarjeta Nu",
                    "account_type": "Tarjeta de crédito",
                    "balance": "400000.00",
                    "credit_limit": "2000000.00",
                    "annual_interest_rate": "24.0000",
                    "statement_day": 15,
                    "payment_due_day": 30,
                    "minimum_payment": "50000.00",
                },
            )
            self.assertEqual(card.status_code, 201)
            card_id = card.json()["id"]
            self.assertEqual(float(card.json()["available_credit"]), 1600000.0)
            self.assertEqual(float(card.json()["estimated_monthly_interest"]), 8000.0)
            loan = client.post(
                "/financial-accounts",
                json={
                    "name": "Préstamo educativo",
                    "account_type": "Préstamo",
                    "balance": "5000000.00",
                    "annual_interest_rate": "12.0000",
                    "payment_due_day": 5,
                    "minimum_payment": "250000.00",
                },
            )
            self.assertEqual(loan.status_code, 201)
            loan_id = loan.json()["id"]
            accounts_summary = client.get("/financial-accounts/summary")
            self.assertEqual(accounts_summary.status_code, 200)
            self.assertEqual(float(accounts_summary.json()["total_debt"]), 5400000.0)
            self.assertEqual(
                float(accounts_summary.json()["total_available_credit"]), 1600000.0
            )
            self.assertEqual(
                float(accounts_summary.json()["estimated_monthly_interest"]), 58000.0
            )
            updated_card = client.put(
                f"/financial-accounts/{card_id}",
                json={
                    "name": "Tarjeta Nu",
                    "account_type": "Tarjeta de crédito",
                    "balance": "350000.00",
                    "credit_limit": "2000000.00",
                    "annual_interest_rate": "24.0000",
                    "statement_day": 15,
                    "payment_due_day": 30,
                    "minimum_payment": "45000.00",
                },
            )
            self.assertEqual(updated_card.status_code, 200)
            self.assertEqual(float(updated_card.json()["available_credit"]), 1650000.0)

            invalid_goal = client.post(
                "/savings-goals",
                json={"name": "Meta inválida", "target_amount": "0"},
            )
            self.assertEqual(invalid_goal.status_code, 422)
            goal = client.post(
                "/savings-goals",
                json={
                    "name": "Fondo de emergencia",
                    "target_amount": "1000000.00",
                    "current_amount": "100000.00",
                    "target_date": savings_date,
                },
            )
            self.assertEqual(goal.status_code, 201)
            goal_id = goal.json()["id"]
            duplicate_goal = client.post(
                "/savings-goals",
                json={"name": "fondo de emergencia", "target_amount": "2000000.00"},
            )
            self.assertEqual(duplicate_goal.status_code, 409)
            contribution = client.post(
                f"/savings-goals/{goal_id}/contributions",
                json={"amount": "150000.00"},
            )
            self.assertEqual(contribution.status_code, 200)
            self.assertEqual(float(contribution.json()["current_amount"]), 250000.0)
            self.assertEqual(float(contribution.json()["percentage_complete"]), 25.0)
            updated_goal = client.put(
                f"/savings-goals/{goal_id}",
                json={
                    "name": "Fondo de emergencia",
                    "target_amount": "1200000.00",
                    "current_amount": "250000.00",
                    "target_date": savings_date,
                },
            )
            self.assertEqual(updated_goal.status_code, 200)
            goals_summary = client.get("/savings-goals/summary")
            self.assertEqual(goals_summary.status_code, 200)
            self.assertEqual(float(goals_summary.json()["total_saved"]), 250000.0)
            self.assertEqual(float(goals_summary.json()["total_remaining"]), 950000.0)

            budget = client.post(
                "/budgets",
                json={"month": now.month, "year": now.year, "amount": "1500000.00"},
            )
            self.assertEqual(budget.status_code, 201)
            budget_id = budget.json()["id"]
            self.assertEqual(
                client.post(
                    "/budgets",
                    json={"month": now.month, "year": now.year, "amount": "100.00"},
                ).status_code,
                409,
            )
            current_budget = client.get("/budgets/current")
            self.assertEqual(current_budget.status_code, 200)
            self.assertEqual(float(current_budget.json()["available"]), 1473000.0)
            self.assertEqual(
                client.put(f"/budgets/{budget_id}", json={"amount": "1600000.00"}).status_code,
                200,
            )

            invalid_event = client.post(
                "/events",
                json={"title": "Inválido", "start_datetime": later, "end_datetime": future},
            )
            self.assertEqual(invalid_event.status_code, 422)
            event = client.post(
                "/events",
                json={"title": "Clase", "start_datetime": future, "end_datetime": later, "location": "Bloque A"},
            )
            self.assertEqual(event.status_code, 201)
            event_id = event.json()["id"]
            self.assertEqual(len(client.get("/events?upcoming=true").json()), 1)
            self.assertEqual(
                client.put(
                    f"/events/{event_id}",
                    json={"title": "Clase de redes", "start_datetime": future, "end_datetime": later, "location": "Bloque B"},
                ).status_code,
                200,
            )

            dashboard = client.get("/dashboard/summary")
            self.assertEqual(dashboard.status_code, 200)
            self.assertEqual(dashboard.json()["pending_tasks"], 0)
            self.assertEqual(dashboard.json()["next_event"]["id"], event_id)
            self.assertEqual(float(dashboard.json()["month_income"]), 810000.0)
            self.assertEqual(float(dashboard.json()["month_cash_flow"]), 783000.0)

            app.dependency_overrides[get_orchestrator] = lambda: AssistantOrchestrator(
                BothAgentsClient()
            )
            try:
                assistant = client.post(
                    "/assistant/chat",
                    json={"message": "Resume mi agenda y mis finanzas", "history": []},
                )
            finally:
                app.dependency_overrides.pop(get_orchestrator, None)
            self.assertEqual(assistant.status_code, 200)
            self.assertEqual(assistant.json()["status"], "completed")
            self.assertEqual(assistant.json()["agents"], ["secretary", "financial"])
            self.assertIn("Clase de redes", assistant.json()["message"])
            self.assertIn("Almuerzo universidad", assistant.json()["message"])

            notification = {
                "text": "Compra aprobada por $45.900 en Mercado Campus con tarjeta 1234.",
                "source": "test_android",
            }
            self.assertEqual(
                client.post("/webhooks/bank-transactions", json=notification).status_code,
                401,
            )
            status = client.get(
                "/webhooks/bank-transactions/status",
                headers={"X-Webhook-Token": os.environ["BANK_WEBHOOK_TOKEN"]},
            )
            self.assertEqual(status.status_code, 200)
            self.assertEqual(status.json()["status"], "ready")
            app.dependency_overrides[get_bank_parser] = lambda: FakeBankParser()
            try:
                webhook = client.post(
                    "/webhooks/bank-transactions",
                    json=notification,
                    headers={"X-Webhook-Token": os.environ["BANK_WEBHOOK_TOKEN"]},
                )
                duplicate = client.post(
                    "/webhooks/bank-transactions",
                    json=notification,
                    headers={"X-Webhook-Token": os.environ["BANK_WEBHOOK_TOKEN"]},
                )
            finally:
                app.dependency_overrides.pop(get_bank_parser, None)
            self.assertEqual(webhook.status_code, 200)
            self.assertEqual(webhook.json()["status"], "created")
            self.assertEqual(webhook.json()["expense"]["description"], "Mercado Campus")
            self.assertEqual(duplicate.json()["status"], "duplicate")
            self.assertEqual(
                duplicate.json()["expense"]["id"], webhook.json()["expense"]["id"]
            )
            self.assertEqual(len(client.get("/expenses").json()), 2)

            backup = client.get("/system/backup")
            self.assertEqual(backup.status_code, 200)
            self.assertIn("recurring_transactions", backup.json()["tables"])
            self.assertEqual(
                client.delete(f"/finances/recurring/{recurring_id}").status_code,
                204,
            )
            restored = client.post(
                "/system/backup/restore",
                json={"backup": backup.json(), "replace_existing": False},
                headers={"X-Confirm-Restore": "restore"},
            )
            self.assertEqual(restored.status_code, 200)
            self.assertGreater(restored.json()["restored_rows"], 0)
            self.assertEqual(len(client.get("/finances/recurring").json()), 1)

        # Una segunda vida útil de FastAPI reutiliza el mismo archivo y confirma persistencia.
        with TestClient(app) as restarted_client:
            self.assertEqual(restarted_client.get(f"/tasks/{task_id}").status_code, 200)
            self.assertEqual(restarted_client.get(f"/expenses/{expense_id}").status_code, 200)
            self.assertEqual(restarted_client.get(f"/incomes/{income_id}").status_code, 200)
            self.assertEqual(
                restarted_client.get(f"/financial-accounts/{card_id}").status_code, 200
            )
            self.assertEqual(
                restarted_client.get(f"/savings-goals/{goal_id}").status_code, 200
            )
            self.assertEqual(restarted_client.get(f"/events/{event_id}").status_code, 200)
            self.assertEqual(restarted_client.delete(f"/tasks/{task_id}").status_code, 204)
            self.assertEqual(restarted_client.delete(f"/expenses/{expense_id}").status_code, 204)
            self.assertEqual(restarted_client.delete(f"/incomes/{income_id}").status_code, 204)
            self.assertEqual(
                restarted_client.delete(f"/financial-accounts/{card_id}").status_code,
                204,
            )
            self.assertEqual(
                restarted_client.delete(f"/financial-accounts/{loan_id}").status_code,
                204,
            )
            self.assertEqual(
                restarted_client.delete(f"/savings-goals/{goal_id}").status_code,
                204,
            )
            self.assertEqual(restarted_client.delete(f"/events/{event_id}").status_code, 204)
            self.assertEqual(restarted_client.delete(f"/budgets/{budget_id}").status_code, 204)
            self.assertEqual(
                restarted_client.delete(f"/finances/recurring/{recurring_id}").status_code,
                204,
            )


def tearDownModule() -> None:
    engine.dispose()
    temporary_directory.cleanup()


if __name__ == "__main__":
    unittest.main()
