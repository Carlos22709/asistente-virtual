/** Cliente CRUD y consultas agregadas para gastos. */

import { Expense, ExpenseCategory, ExpenseInput, FinanceSummary } from "@/types";
import { queryString, request } from "./api";

export const expenseService = {
  list: (filters: { category?: ExpenseCategory; date_from?: string; date_to?: string } = {}) =>
    request<Expense[]>(`/expenses${queryString(filters)}`),
  summary: () => request<FinanceSummary>("/expenses/summary"),
  create: (input: ExpenseInput) =>
    request<Expense>("/expenses", { method: "POST", body: JSON.stringify(input) }),
  update: (id: number, input: ExpenseInput) =>
    request<Expense>(`/expenses/${id}`, { method: "PUT", body: JSON.stringify(input) }),
  remove: (id: number) => request<void>(`/expenses/${id}`, { method: "DELETE" }),
};
