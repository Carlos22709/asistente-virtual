/** Acceso a presupuestos y al presupuesto vigente. */

import { Budget, CurrentBudget } from "@/types";
import { request } from "./api";

export const budgetService = {
  current: () => request<CurrentBudget | null>("/budgets/current"),
  list: () => request<Budget[]>("/budgets"),
  create: (month: number, year: number, amount: string) =>
    request<Budget>("/budgets", { method: "POST", body: JSON.stringify({ month, year, amount }) }),
  update: (id: number, amount: string) =>
    request<Budget>(`/budgets/${id}`, { method: "PUT", body: JSON.stringify({ amount }) }),
  remove: (id: number) => request<void>(`/budgets/${id}`, { method: "DELETE" }),
};
