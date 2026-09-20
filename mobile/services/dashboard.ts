/** Obtiene el resumen consolidado para la pantalla de inicio. */

import { DashboardSummary } from "@/types";
import { request } from "./api";

export const dashboardService = {
  summary: () => request<DashboardSummary>("/dashboard/summary"),
};
