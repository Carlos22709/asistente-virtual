/** Contratos TypeScript que reflejan los esquemas publicados por el backend. */

export type TaskPriority = "Baja" | "Media" | "Alta";
export type TaskStatus = "Pendiente" | "En progreso" | "Completada";
export type ExpenseCategory =
  | "Comida"
  | "Transporte"
  | "Universidad"
  | "Entretenimiento"
  | "Compras"
  | "Salud"
  | "Otros";
export type IncomeCategory =
  | "Salario"
  | "Trabajo independiente"
  | "Beca"
  | "Apoyo familiar"
  | "Reembolso"
  | "Inversión"
  | "Otros";

export interface Task {
  id: number;
  title: string;
  description: string | null;
  due_date: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  completed: boolean;
  created_at: string;
}

export interface TaskInput {
  title: string;
  description?: string | null;
  due_date?: string | null;
  priority: TaskPriority;
  status?: TaskStatus;
  completed?: boolean;
}

export interface Expense {
  id: number;
  description: string;
  amount: string;
  category: ExpenseCategory;
  date: string;
  note: string | null;
  created_at: string;
}

export type ExpenseInput = Omit<Expense, "id" | "created_at" | "amount"> & { amount: string };

export interface FinanceSummary {
  today: string;
  week: string;
  month: string;
}

export interface Income {
  id: number;
  description: string;
  amount: string;
  category: IncomeCategory;
  date: string;
  note: string | null;
  created_at: string;
}

export type IncomeInput = Omit<Income, "id" | "created_at" | "amount"> & { amount: string };

export interface CashFlowSummary {
  income_month: string;
  expenses_month: string;
  net_month: string;
  projected_recurring_income: string;
  projected_recurring_expenses: string;
  projected_obligations: string;
  projected_available: string;
  obligations_due_count: number;
  unconfigured_obligations_count: number;
  projection_end_date: string;
}

export type TransactionKind = "Ingreso" | "Gasto";
export type RecurrenceFrequency = "Semanal" | "Mensual" | "Anual";

export interface RecurringTransaction {
  id: number;
  description: string;
  amount: string;
  kind: TransactionKind;
  category: IncomeCategory | ExpenseCategory;
  frequency: RecurrenceFrequency;
  interval: number;
  start_date: string;
  end_date: string | null;
  active: boolean;
  note: string | null;
  created_at: string;
}

export type RecurringTransactionInput = Omit<
  RecurringTransaction,
  "id" | "created_at" | "amount"
> & { amount: string };

export interface CashFlowForecastPoint {
  period_start: string;
  period_end: string;
  recorded_income: string;
  recorded_expenses: string;
  recurring_income: string;
  recurring_expenses: string;
  debt_obligations: string;
  projected_net: string;
  projected_available: string;
  unconfigured_obligations_count: number;
}

export interface CashFlowForecast {
  generated_at: string;
  months: number;
  points: CashFlowForecastPoint[];
}

export type FinancialAccountType = "Tarjeta de crédito" | "Préstamo";

export interface FinancialAccount {
  id: number;
  name: string;
  account_type: FinancialAccountType;
  balance: string;
  credit_limit: string | null;
  annual_interest_rate: string;
  statement_day: number | null;
  payment_due_day: number;
  minimum_payment: string | null;
  available_credit: string | null;
  estimated_monthly_interest: string;
  next_statement_date: string | null;
  next_payment_due_date: string;
  created_at: string;
}

export type FinancialAccountInput = Pick<
  FinancialAccount,
  "name" | "account_type" | "balance" | "credit_limit" | "annual_interest_rate" | "statement_day" | "payment_due_day" | "minimum_payment"
>;

export interface FinancialAccountsSummary {
  total_debt: string;
  total_available_credit: string;
  estimated_monthly_interest: string;
  accounts: FinancialAccount[];
}

export interface SavingsGoal {
  id: number;
  name: string;
  target_amount: string;
  current_amount: string;
  target_date: string | null;
  remaining_amount: string;
  percentage_complete: string;
  days_remaining: number | null;
  created_at: string;
}

export type SavingsGoalInput = Pick<
  SavingsGoal,
  "name" | "target_amount" | "current_amount" | "target_date"
>;

export interface SavingsGoalsSummary {
  total_target: string;
  total_saved: string;
  total_remaining: string;
  percentage_complete: string;
  goals: SavingsGoal[];
}

export interface Budget {
  id: number;
  month: number;
  year: number;
  amount: string;
}

export interface CurrentBudget extends Budget {
  spent: string;
  available: string;
  percentage_used: string;
}

export interface EventItem {
  id: number;
  title: string;
  description: string | null;
  start_datetime: string;
  end_datetime: string | null;
  location: string | null;
  created_at: string;
}

export type EventInput = Omit<EventItem, "id" | "created_at">;

export interface DashboardSummary {
  pending_tasks: number;
  upcoming_tasks: Task[];
  today_spent: string;
  week_spent: string;
  month_income: string;
  month_cash_flow: string;
  month_projected_obligations: string;
  month_projected_available: string;
  unconfigured_obligations_count: number;
  next_event: EventItem | null;
  current_budget: CurrentBudget | null;
}

export type AssistantAgent = "secretary" | "financial";

export interface AssistantConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantChatRequest {
  message: string;
  history: AssistantConversationMessage[];
}

export interface AssistantChatResponse {
  message: string;
  agents: AssistantAgent[];
  routing_reason: string;
  status: "completed";
}

export interface AssistantTranscriptionResponse {
  text: string;
  language: string;
}

export interface ComponentStatus {
  status: "ready" | "missing" | "error";
  detail: string;
}

export interface SystemStatus {
  status: "ready" | "degraded";
  checked_at: string;
  database_provider: string;
  api_auth_enabled: boolean;
  components: Record<string, ComponentStatus>;
}

export interface BackupDocument {
  version: 1;
  exported_at: string;
  tables: Record<string, Array<Record<string, unknown>>>;
}

export interface BackupRestoreResult {
  status: "restored";
  restored_rows: number;
  tables: Record<string, number>;
}
