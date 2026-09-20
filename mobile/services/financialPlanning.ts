/** Consulta recurrencias y proyecciones de flujo de caja. */

import {
  CashFlowForecast,
  RecurringTransaction,
  RecurringTransactionInput,
} from "@/types";
import { queryString, request } from "./api";

export const financialPlanningService = {
  forecast: (months = 6) =>
    request<CashFlowForecast>("/finances/forecast" + queryString({ months })),
  recurring: {
    list: () => request<RecurringTransaction[]>("/finances/recurring"),
    create: (input: RecurringTransactionInput) =>
      request<RecurringTransaction>("/finances/recurring", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    update: (id: number, input: RecurringTransactionInput) =>
      request<RecurringTransaction>("/finances/recurring/" + id, {
        method: "PUT",
        body: JSON.stringify(input),
      }),
    remove: (id: number) =>
      request<void>("/finances/recurring/" + id, { method: "DELETE" }),
  },
};
