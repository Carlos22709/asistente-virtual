/** Cliente CRUD y flujo de caja para ingresos. */

import { CashFlowSummary, Income, IncomeInput } from "@/types";
import { request } from "./api";

export const incomeService = {
  list: () => request<Income[]>("/incomes"),
  cashFlow: () => request<CashFlowSummary>("/incomes/cash-flow"),
  create: (input: IncomeInput) =>
    request<Income>("/incomes", { method: "POST", body: JSON.stringify(input) }),
  update: (id: number, input: IncomeInput) =>
    request<Income>(`/incomes/${id}`, { method: "PUT", body: JSON.stringify(input) }),
  remove: (id: number) => request<void>(`/incomes/${id}`, { method: "DELETE" }),
};
