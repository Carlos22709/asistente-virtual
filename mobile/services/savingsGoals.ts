/** Cliente para metas de ahorro y sus aportes. */

import { SavingsGoal, SavingsGoalInput, SavingsGoalsSummary } from "@/types";
import { request } from "./api";

export const savingsGoalService = {
  summary: () => request<SavingsGoalsSummary>("/savings-goals/summary"),
  create: (input: SavingsGoalInput) =>
    request<SavingsGoal>("/savings-goals", { method: "POST", body: JSON.stringify(input) }),
  update: (id: number, input: SavingsGoalInput) =>
    request<SavingsGoal>(`/savings-goals/${id}`, { method: "PUT", body: JSON.stringify(input) }),
  contribute: (id: number, amount: string) =>
    request<SavingsGoal>(`/savings-goals/${id}/contributions`, {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  remove: (id: number) => request<void>(`/savings-goals/${id}`, { method: "DELETE" }),
};
