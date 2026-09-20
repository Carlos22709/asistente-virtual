/** Cliente CRUD para tarjetas de credito y prestamos. */

import { FinancialAccount, FinancialAccountInput, FinancialAccountsSummary } from "@/types";
import { request } from "./api";

export const financialAccountService = {
  summary: () => request<FinancialAccountsSummary>("/financial-accounts/summary"),
  create: (input: FinancialAccountInput) =>
    request<FinancialAccount>("/financial-accounts", { method: "POST", body: JSON.stringify(input) }),
  update: (id: number, input: FinancialAccountInput) =>
    request<FinancialAccount>(`/financial-accounts/${id}`, { method: "PUT", body: JSON.stringify(input) }),
  remove: (id: number) => request<void>(`/financial-accounts/${id}`, { method: "DELETE" }),
};
