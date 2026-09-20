/** Panel financiero para movimientos, obligaciones, presupuestos y ahorro. */

import { useCallback, useState } from "react";
import { Alert, RefreshControl, StyleSheet, Switch, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
import { Card, Chips, Field, FormModal, LoadState, PageHeader, PrimaryButton, Screen, sharedStyles } from "@/components/ui";
import { colors } from "@/constants/theme";
import { budgetService } from "@/services/budgets";
import { expenseService } from "@/services/expenses";
import { financialAccountService } from "@/services/financialAccounts";
import { financialPlanningService } from "@/services/financialPlanning";
import { incomeService } from "@/services/incomes";
import { syncFinancialReminders } from "@/services/notifications";
import { savingsGoalService } from "@/services/savingsGoals";
import {
  CashFlowForecast,
  CashFlowSummary,
  CurrentBudget,
  Expense,
  ExpenseCategory,
  ExpenseInput,
  FinanceSummary,
  FinancialAccount,
  FinancialAccountInput,
  FinancialAccountsSummary,
  Income,
  IncomeCategory,
  IncomeInput,
  RecurrenceFrequency,
  RecurringTransaction,
  RecurringTransactionInput,
  SavingsGoal,
  SavingsGoalInput,
  SavingsGoalsSummary,
  TransactionKind,
} from "@/types";
import { formatDate, formatMoney, todayInput } from "@/utils/format";

const categories = ["Comida", "Transporte", "Universidad", "Entretenimiento", "Compras", "Salud", "Otros"] as const;
const categoryFilters = ["Todas", ...categories] as const;
const incomeCategories = ["Salario", "Trabajo independiente", "Beca", "Apoyo familiar", "Reembolso", "Inversión", "Otros"] as const;
const accountTypes = ["Tarjeta de crédito", "Préstamo"] as const;
const transactionKinds = ["Ingreso", "Gasto"] as const;
const recurrenceFrequencies = ["Semanal", "Mensual", "Anual"] as const;

export default function FinancesScreen() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [incomes, setIncomes] = useState<Income[]>([]);
  const [cashFlow, setCashFlow] = useState<CashFlowSummary | null>(null);
  const [forecast, setForecast] = useState<CashFlowForecast | null>(null);
  const [recurringItems, setRecurringItems] = useState<RecurringTransaction[]>([]);
  const [accountsSummary, setAccountsSummary] = useState<FinancialAccountsSummary | null>(null);
  const [savingsSummary, setSavingsSummary] = useState<SavingsGoalsSummary | null>(null);
  const [budget, setBudget] = useState<CurrentBudget | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<(typeof categoryFilters)[number]>("Todas");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [expenseModal, setExpenseModal] = useState(false);
  const [budgetModal, setBudgetModal] = useState(false);
  const [incomeModal, setIncomeModal] = useState(false);
  const [accountModal, setAccountModal] = useState(false);
  const [goalModal, setGoalModal] = useState(false);
  const [contributionModal, setContributionModal] = useState(false);
  const [recurringModal, setRecurringModal] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);
  const [editingIncome, setEditingIncome] = useState<Income | null>(null);
  const [editingAccount, setEditingAccount] = useState<FinancialAccount | null>(null);
  const [editingGoal, setEditingGoal] = useState<SavingsGoal | null>(null);
  const [contributionGoal, setContributionGoal] = useState<SavingsGoal | null>(null);
  const [editingRecurring, setEditingRecurring] = useState<RecurringTransaction | null>(null);
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState<ExpenseCategory>("Comida");
  const [expenseDate, setExpenseDate] = useState(todayInput());
  const [note, setNote] = useState("");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [incomeDescription, setIncomeDescription] = useState("");
  const [incomeAmount, setIncomeAmount] = useState("");
  const [incomeCategory, setIncomeCategory] = useState<IncomeCategory>("Salario");
  const [incomeDate, setIncomeDate] = useState(todayInput());
  const [incomeNote, setIncomeNote] = useState("");
  const [accountName, setAccountName] = useState("");
  const [accountType, setAccountType] = useState<(typeof accountTypes)[number]>("Tarjeta de crédito");
  const [accountBalance, setAccountBalance] = useState("");
  const [creditLimit, setCreditLimit] = useState("");
  const [interestRate, setInterestRate] = useState("");
  const [statementDay, setStatementDay] = useState("");
  const [paymentDueDay, setPaymentDueDay] = useState("");
  const [minimumPayment, setMinimumPayment] = useState("");
  const [goalName, setGoalName] = useState("");
  const [goalTarget, setGoalTarget] = useState("");
  const [goalCurrent, setGoalCurrent] = useState("");
  const [goalDate, setGoalDate] = useState("");
  const [contributionAmount, setContributionAmount] = useState("");
  const [recurringKind, setRecurringKind] = useState<TransactionKind>("Gasto");
  const [recurringDescription, setRecurringDescription] = useState("");
  const [recurringAmount, setRecurringAmount] = useState("");
  const [recurringCategory, setRecurringCategory] = useState<ExpenseCategory | IncomeCategory>("Otros");
  const [recurringFrequency, setRecurringFrequency] = useState<RecurrenceFrequency>("Mensual");
  const [recurringInterval, setRecurringInterval] = useState("1");
  const [recurringStart, setRecurringStart] = useState(todayInput());
  const [recurringEnd, setRecurringEnd] = useState("");
  const [recurringActive, setRecurringActive] = useState(true);
  const [recurringNote, setRecurringNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const load = useCallback(async (pull = false) => {
    pull ? setRefreshing(true) : setLoading(true); setError("");
    try {
      const [items, totals, current, incomeItems, currentCashFlow, accountTotals, goalTotals, recurring, cashForecast] = await Promise.all([
        expenseService.list({ category: categoryFilter === "Todas" ? undefined : categoryFilter, date_from: from || undefined, date_to: to || undefined }),
        expenseService.summary(),
        budgetService.current(),
        incomeService.list(),
        incomeService.cashFlow(),
        financialAccountService.summary(),
        savingsGoalService.summary(),
        financialPlanningService.recurring.list(),
        financialPlanningService.forecast(6),
      ]);
      setExpenses(items); setSummary(totals); setBudget(current); setIncomes(incomeItems); setCashFlow(currentCashFlow); setAccountsSummary(accountTotals); setSavingsSummary(goalTotals); setRecurringItems(recurring); setForecast(cashForecast);
      void syncFinancialReminders(accountTotals.accounts, currentCashFlow);
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudieron cargar tus finanzas."); }
    finally { setLoading(false); setRefreshing(false); }
  }, [categoryFilter, from, to]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  const openExpense = (expense?: Expense) => {
    setNotice("");
    setEditing(expense ?? null); setDescription(expense?.description ?? ""); setAmount(expense?.amount ?? "");
    setCategory(expense?.category ?? "Comida"); setExpenseDate(expense?.date ?? todayInput()); setNote(expense?.note ?? "");
    setFormError(""); setExpenseModal(true);
  };

  const saveExpense = async () => {
    const numericAmount = Number(amount.replace(",", "."));
    if (!description.trim()) return setFormError("Escribe una descripción.");
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) return setFormError("El monto debe ser mayor que cero.");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(expenseDate)) return setFormError("Usa una fecha con formato AAAA-MM-DD.");
    const payload: ExpenseInput = { description: description.trim(), amount: numericAmount.toFixed(2), category, date: expenseDate, note: note.trim() || null };
    setSaving(true); setFormError("");
    try {
      if (editing) await expenseService.update(editing.id, payload); else await expenseService.create(payload);
      setNotice(editing ? "Gasto actualizado." : "Gasto registrado.");
      setExpenseModal(false); await load();
    } catch (err) { setFormError(err instanceof Error ? err.message : "No se pudo guardar el gasto."); }
    finally { setSaving(false); }
  };

  const saveBudget = async () => {
    const numericAmount = Number(budgetAmount.replace(",", "."));
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) return setFormError("El presupuesto debe ser mayor que cero.");
    setSaving(true); setFormError("");
    try {
      if (budget) await budgetService.update(budget.id, numericAmount.toFixed(2));
      else { const now = new Date(); await budgetService.create(Number(new Intl.DateTimeFormat("en", { month: "numeric", timeZone: "America/Bogota" }).format(now)), Number(new Intl.DateTimeFormat("en", { year: "numeric", timeZone: "America/Bogota" }).format(now)), numericAmount.toFixed(2)); }
      setNotice(budget ? "Presupuesto actualizado." : "Presupuesto creado.");
      setBudgetModal(false); await load();
    } catch (err) { setFormError(err instanceof Error ? err.message : "No se pudo guardar el presupuesto."); }
    finally { setSaving(false); }
  };

  const openIncome = (income?: Income) => {
    setNotice(""); setEditingIncome(income ?? null);
    setIncomeDescription(income?.description ?? ""); setIncomeAmount(income?.amount ?? "");
    setIncomeCategory(income?.category ?? "Salario"); setIncomeDate(income?.date ?? todayInput());
    setIncomeNote(income?.note ?? ""); setFormError(""); setIncomeModal(true);
  };

  const saveIncome = async () => {
    const numericAmount = Number(incomeAmount.replace(",", "."));
    if (!incomeDescription.trim()) return setFormError("Escribe una descripción.");
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) return setFormError("El monto debe ser mayor que cero.");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(incomeDate)) return setFormError("Usa una fecha con formato AAAA-MM-DD.");
    const payload: IncomeInput = { description: incomeDescription.trim(), amount: numericAmount.toFixed(2), category: incomeCategory, date: incomeDate, note: incomeNote.trim() || null };
    setSaving(true); setFormError("");
    try {
      if (editingIncome) await incomeService.update(editingIncome.id, payload); else await incomeService.create(payload);
      setNotice(editingIncome ? "Ingreso actualizado." : "Ingreso registrado.");
      setIncomeModal(false); await load();
    } catch (err) { setFormError(err instanceof Error ? err.message : "No se pudo guardar el ingreso."); }
    finally { setSaving(false); }
  };

  const removeExpense = (expense: Expense) => Alert.alert("Eliminar gasto", "¿Seguro que quieres eliminar este gasto?", [
    { text: "Cancelar", style: "cancel" },
    { text: "Eliminar", style: "destructive", onPress: async () => {
      try { await expenseService.remove(expense.id); setNotice("Gasto eliminado."); await load(); }
      catch (err) { Alert.alert("No fue posible", err instanceof Error ? err.message : "Intenta de nuevo."); }
    } },
  ]);

  const removeBudget = () => budget && Alert.alert("Eliminar presupuesto", "¿Seguro que quieres eliminar el presupuesto de este mes?", [
    { text: "Cancelar", style: "cancel" },
    { text: "Eliminar", style: "destructive", onPress: async () => {
      try { await budgetService.remove(budget.id); setNotice("Presupuesto eliminado."); await load(); }
      catch (err) { Alert.alert("No fue posible", err instanceof Error ? err.message : "Intenta de nuevo."); }
    } },
  ]);

  const removeIncome = (income: Income) => Alert.alert("Eliminar ingreso", "¿Seguro que quieres eliminar este ingreso?", [
    { text: "Cancelar", style: "cancel" },
    { text: "Eliminar", style: "destructive", onPress: async () => {
      try { await incomeService.remove(income.id); setNotice("Ingreso eliminado."); await load(); }
      catch (err) { Alert.alert("No fue posible", err instanceof Error ? err.message : "Intenta de nuevo."); }
    } },
  ]);

  const openAccount = (account?: FinancialAccount) => {
    setNotice(""); setEditingAccount(account ?? null); setAccountName(account?.name ?? "");
    setAccountType(account?.account_type ?? "Tarjeta de crédito"); setAccountBalance(account?.balance ?? "");
    setCreditLimit(account?.credit_limit ?? ""); setInterestRate(account?.annual_interest_rate ?? "");
    setStatementDay(account?.statement_day?.toString() ?? ""); setPaymentDueDay(account?.payment_due_day?.toString() ?? "");
    setMinimumPayment(account?.minimum_payment ?? ""); setFormError(""); setAccountModal(true);
  };

  const saveAccount = async () => {
    const balanceValue = Number(accountBalance.replace(",", "."));
    const limitValue = Number(creditLimit.replace(",", "."));
    const rateValue = interestRate.trim() ? Number(interestRate.replace(",", ".")) : 0;
    const statementValue = Number(statementDay);
    const dueValue = Number(paymentDueDay);
    const minimumValue = minimumPayment.trim() ? Number(minimumPayment.replace(",", ".")) : null;
    if (!accountName.trim()) return setFormError("Escribe un nombre para la cuenta.");
    if (!Number.isFinite(balanceValue) || balanceValue < 0) return setFormError("La deuda no puede ser negativa.");
    if (!Number.isFinite(rateValue) || rateValue < 0 || rateValue > 200) return setFormError("La tasa anual debe estar entre 0 y 200.");
    if (!Number.isInteger(dueValue) || dueValue < 1 || dueValue > 31) return setFormError("El día de pago debe estar entre 1 y 31.");
    if (accountType === "Tarjeta de crédito" && (!Number.isFinite(limitValue) || limitValue <= 0)) return setFormError("Indica un cupo mayor que cero.");
    if (accountType === "Tarjeta de crédito" && (!Number.isInteger(statementValue) || statementValue < 1 || statementValue > 31)) return setFormError("El día de corte debe estar entre 1 y 31.");
    if (balanceValue > 0 && (minimumValue === null || !Number.isFinite(minimumValue) || minimumValue <= 0)) return setFormError("Indica el pago mínimo o la cuota mensual para proyectar tu dinero disponible.");
    const payload: FinancialAccountInput = {
      name: accountName.trim(), account_type: accountType, balance: balanceValue.toFixed(2),
      credit_limit: accountType === "Tarjeta de crédito" ? limitValue.toFixed(2) : null,
      annual_interest_rate: rateValue.toFixed(4), statement_day: accountType === "Tarjeta de crédito" ? statementValue : null,
      payment_due_day: dueValue, minimum_payment: minimumValue === null ? null : minimumValue.toFixed(2),
    };
    setSaving(true); setFormError("");
    try {
      if (editingAccount) await financialAccountService.update(editingAccount.id, payload); else await financialAccountService.create(payload);
      setNotice(editingAccount ? "Cuenta financiera actualizada." : "Cuenta financiera registrada.");
      setAccountModal(false); await load();
    } catch (err) { setFormError(err instanceof Error ? err.message : "No se pudo guardar la cuenta."); }
    finally { setSaving(false); }
  };

  const removeAccount = (account: FinancialAccount) => Alert.alert("Eliminar cuenta", "¿Seguro que quieres eliminar esta tarjeta o préstamo?", [
    { text: "Cancelar", style: "cancel" },
    { text: "Eliminar", style: "destructive", onPress: async () => {
      try { await financialAccountService.remove(account.id); setNotice("Cuenta financiera eliminada."); await load(); }
      catch (err) { Alert.alert("No fue posible", err instanceof Error ? err.message : "Intenta de nuevo."); }
    } },
  ]);

  const openGoal = (goal?: SavingsGoal) => {
    setNotice(""); setEditingGoal(goal ?? null); setGoalName(goal?.name ?? "");
    setGoalTarget(goal?.target_amount ?? ""); setGoalCurrent(goal?.current_amount ?? "0");
    setGoalDate(goal?.target_date ?? ""); setFormError(""); setGoalModal(true);
  };

  const saveGoal = async () => {
    const targetValue = Number(goalTarget.replace(",", "."));
    const currentValue = Number(goalCurrent.replace(",", "."));
    if (!goalName.trim()) return setFormError("Escribe un nombre para la meta.");
    if (!Number.isFinite(targetValue) || targetValue <= 0) return setFormError("El objetivo debe ser mayor que cero.");
    if (!Number.isFinite(currentValue) || currentValue < 0) return setFormError("El ahorro actual no puede ser negativo.");
    if (goalDate && !/^\d{4}-\d{2}-\d{2}$/.test(goalDate)) return setFormError("Usa una fecha con formato AAAA-MM-DD.");
    const payload: SavingsGoalInput = { name: goalName.trim(), target_amount: targetValue.toFixed(2), current_amount: currentValue.toFixed(2), target_date: goalDate || null };
    setSaving(true); setFormError("");
    try {
      if (editingGoal) await savingsGoalService.update(editingGoal.id, payload); else await savingsGoalService.create(payload);
      setNotice(editingGoal ? "Meta actualizada." : "Meta de ahorro creada.");
      setGoalModal(false); await load();
    } catch (err) { setFormError(err instanceof Error ? err.message : "No se pudo guardar la meta."); }
    finally { setSaving(false); }
  };

  const openContribution = (goal: SavingsGoal) => {
    setContributionGoal(goal); setContributionAmount(""); setFormError(""); setContributionModal(true);
  };

  const saveContribution = async () => {
    const amountValue = Number(contributionAmount.replace(",", "."));
    if (!contributionGoal) return;
    if (!Number.isFinite(amountValue) || amountValue <= 0) return setFormError("El aporte debe ser mayor que cero.");
    setSaving(true); setFormError("");
    try {
      await savingsGoalService.contribute(contributionGoal.id, amountValue.toFixed(2));
      setNotice(`Aporte agregado a ${contributionGoal.name}.`); setContributionModal(false); await load();
    } catch (err) { setFormError(err instanceof Error ? err.message : "No se pudo registrar el aporte."); }
    finally { setSaving(false); }
  };

  const removeGoal = (goal: SavingsGoal) => Alert.alert("Eliminar meta", "¿Seguro que quieres eliminar esta meta de ahorro?", [
    { text: "Cancelar", style: "cancel" },
    { text: "Eliminar", style: "destructive", onPress: async () => {
      try { await savingsGoalService.remove(goal.id); setNotice("Meta eliminada."); await load(); }
      catch (err) { Alert.alert("No fue posible", err instanceof Error ? err.message : "Intenta de nuevo."); }
    } },
  ]);

  const selectRecurringKind = (kind: TransactionKind) => {
    setRecurringKind(kind);
    setRecurringCategory(kind === "Ingreso" ? "Salario" : "Otros");
  };

  const openRecurring = (item?: RecurringTransaction) => {
    setNotice("");
    setEditingRecurring(item ?? null);
    setRecurringKind(item?.kind ?? "Gasto");
    setRecurringDescription(item?.description ?? "");
    setRecurringAmount(item?.amount ?? "");
    setRecurringCategory(item?.category ?? "Otros");
    setRecurringFrequency(item?.frequency ?? "Mensual");
    setRecurringInterval(item?.interval.toString() ?? "1");
    setRecurringStart(item?.start_date ?? todayInput());
    setRecurringEnd(item?.end_date ?? "");
    setRecurringActive(item?.active ?? true);
    setRecurringNote(item?.note ?? "");
    setFormError("");
    setRecurringModal(true);
  };

  const saveRecurring = async () => {
    const amountValue = Number(recurringAmount.replace(",", "."));
    const intervalValue = Number(recurringInterval);
    if (!recurringDescription.trim()) return setFormError("Escribe una descripción.");
    if (!Number.isFinite(amountValue) || amountValue <= 0) return setFormError("El monto debe ser mayor que cero.");
    if (!Number.isInteger(intervalValue) || intervalValue < 1 || intervalValue > 52) return setFormError("El intervalo debe estar entre 1 y 52.");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(recurringStart)) return setFormError("Usa una fecha inicial con formato AAAA-MM-DD.");
    if (recurringEnd && !/^\d{4}-\d{2}-\d{2}$/.test(recurringEnd)) return setFormError("Usa una fecha final con formato AAAA-MM-DD.");
    if (recurringEnd && recurringEnd < recurringStart) return setFormError("La fecha final no puede ser anterior a la inicial.");
    const payload: RecurringTransactionInput = {
      description: recurringDescription.trim(),
      amount: amountValue.toFixed(2),
      kind: recurringKind,
      category: recurringCategory,
      frequency: recurringFrequency,
      interval: intervalValue,
      start_date: recurringStart,
      end_date: recurringEnd || null,
      active: recurringActive,
      note: recurringNote.trim() || null,
    };
    setSaving(true); setFormError("");
    try {
      if (editingRecurring) await financialPlanningService.recurring.update(editingRecurring.id, payload);
      else await financialPlanningService.recurring.create(payload);
      setNotice(editingRecurring ? "Movimiento recurrente actualizado." : "Movimiento recurrente creado.");
      setRecurringModal(false);
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "No se pudo guardar el movimiento recurrente.");
    } finally {
      setSaving(false);
    }
  };

  const removeRecurring = (item: RecurringTransaction) => Alert.alert(
    "Eliminar recurrencia",
    "¿Seguro que quieres dejar de proyectar este movimiento?",
    [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Eliminar",
        style: "destructive",
        onPress: async () => {
          try {
            await financialPlanningService.recurring.remove(item.id);
            setNotice("Movimiento recurrente eliminado.");
            await load();
          } catch (err) {
            Alert.alert("No fue posible", err instanceof Error ? err.message : "Intenta de nuevo.");
          }
        },
      },
    ],
  );

  const openBudget = () => { setNotice(""); setBudgetAmount(budget?.amount ?? ""); setFormError(""); setBudgetModal(true); };

  return (
    <Screen refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void load(true)} tintColor={colors.primary} />}>
      <PageHeader eyebrow="Claridad para decidir" title="Finanzas" subtitle="Tus ingresos, gastos y presupuesto, sin complicaciones." />
      <View style={styles.mainActions}><PrimaryButton label="＋ Gasto" onPress={() => openExpense()} /><PrimaryButton label="＋ Ingreso" onPress={() => openIncome()} variant="soft" /><PrimaryButton label="＋ Recurrente" onPress={() => openRecurring()} variant="soft" /><PrimaryButton label="＋ Tarjeta o préstamo" onPress={() => openAccount()} variant="soft" /><PrimaryButton label="＋ Meta de ahorro" onPress={() => openGoal()} variant="soft" /></View>
      {notice ? <Text style={sharedStyles.success}>{notice}</Text> : null}
      <LoadState loading={loading} error={error} onRetry={() => void load()} />
      {!loading && !error && summary ? (
        <View style={styles.stats}>
          <Card style={[styles.stat, styles.pink]}><Text style={styles.statLabel}>Hoy</Text><Text style={styles.statValue}>{formatMoney(summary.today)}</Text></Card>
          <Card style={[styles.stat, styles.cream]}><Text style={styles.statLabel}>Semana</Text><Text style={styles.statValue}>{formatMoney(summary.week)}</Text></Card>
          <Card style={[styles.stat, styles.blue]}><Text style={styles.statLabel}>Mes</Text><Text style={styles.statValue}>{formatMoney(summary.month)}</Text></Card>
        </View>
      ) : null}

      {!loading && !error && cashFlow ? <>
        <Text style={sharedStyles.sectionTitle}>Flujo de caja del mes</Text>
        <Card style={styles.blue}>
          <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Ingresos</Text><Text style={styles.cashIncome}>{formatMoney(cashFlow.income_month)}</Text></View>
          <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Gastos</Text><Text style={styles.cashExpense}>{formatMoney(cashFlow.expenses_month)}</Text></View>
          {Number(cashFlow.projected_recurring_income) > 0 ? <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Ingresos recurrentes pendientes</Text><Text style={styles.cashIncome}>{formatMoney(cashFlow.projected_recurring_income)}</Text></View> : null}
          {Number(cashFlow.projected_recurring_expenses) > 0 ? <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Gastos recurrentes pendientes</Text><Text style={styles.cashExpense}>{formatMoney(cashFlow.projected_recurring_expenses)}</Text></View> : null}
          <View style={styles.cashDivider} />
          <View style={sharedStyles.between}><Text style={sharedStyles.body}>Flujo neto</Text><Text style={[styles.cashNet, Number(cashFlow.net_month) < 0 && styles.negative]}>{formatMoney(cashFlow.net_month)}</Text></View>
          <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Pagos pendientes hasta {formatDate(`${cashFlow.projection_end_date}T12:00:00-05:00`)}</Text><Text style={styles.cashExpense}>{formatMoney(cashFlow.projected_obligations)}</Text></View>
          <View style={styles.cashDivider} />
          <View style={sharedStyles.between}><Text style={sharedStyles.body}>Disponible proyectado</Text><Text style={[styles.cashNet, Number(cashFlow.projected_available) < 0 && styles.negative]}>{formatMoney(cashFlow.projected_available)}</Text></View>
          <Text style={sharedStyles.muted}>{cashFlow.obligations_due_count} pago(s) incluidos en la proyección.</Text>
          {cashFlow.unconfigured_obligations_count > 0 ? <Text style={sharedStyles.error}>{cashFlow.unconfigured_obligations_count} cuenta(s) vencen este mes sin cuota configurada y no están incluidas.</Text> : null}
        </Card>
      </> : null}

      {!loading && !error && forecast ? <>
        <Text style={sharedStyles.sectionTitle}>Proyección de {forecast.months} meses</Text>
        {forecast.points.map((point) => (
          <Card key={point.period_start} style={Number(point.projected_available) < 0 ? styles.warningCard : undefined}>
            <View style={sharedStyles.between}>
              <Text style={styles.expenseTitle}>{formatDate(point.period_start + "T12:00:00-05:00")}</Text>
              <Text style={[styles.cashNet, Number(point.projected_available) < 0 && styles.negative]}>
                {formatMoney(point.projected_available)}
              </Text>
            </View>
            <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Ingresos previstos</Text><Text style={styles.cashIncome}>{formatMoney(Number(point.recorded_income) + Number(point.recurring_income))}</Text></View>
            <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Gastos y pagos</Text><Text style={styles.cashExpense}>{formatMoney(Number(point.recorded_expenses) + Number(point.recurring_expenses) + Number(point.debt_obligations))}</Text></View>
            <Text style={sharedStyles.muted}>Flujo del mes: {formatMoney(point.projected_net)} · disponible acumulado</Text>
            {point.unconfigured_obligations_count > 0 ? <Text style={sharedStyles.error}>{point.unconfigured_obligations_count} deuda(s) sin cuota no están incluidas.</Text> : null}
          </Card>
        ))}
      </> : null}

      {!loading && !error ? <>
        <Text style={sharedStyles.sectionTitle}>Movimientos recurrentes</Text>
        {recurringItems.length === 0 ? (
          <LoadState loading={false} error="" empty="Añade salario, arriendo, suscripciones u otros movimientos para proyectar los próximos meses." onRetry={() => void load()} />
        ) : recurringItems.map((item) => (
          <Card key={item.id}>
            <View style={sharedStyles.between}>
              <Text style={styles.expenseTitle}>{item.description}</Text>
              <Text style={item.kind === "Ingreso" ? styles.incomeAmount : styles.expenseAmount}>{item.kind === "Ingreso" ? "+" : "−"}{formatMoney(item.amount)}</Text>
            </View>
            <Text style={sharedStyles.muted}>
              {item.frequency}{item.interval > 1 ? " cada " + item.interval + " periodos" : ""} · desde {formatDate(item.start_date + "T12:00:00-05:00")}
            </Text>
            <Text style={sharedStyles.body}>{item.category} · {item.active ? "Activo" : "Pausado"}{item.end_date ? " · hasta " + formatDate(item.end_date + "T12:00:00-05:00") : ""}</Text>
            <View style={sharedStyles.actions}><PrimaryButton label="Editar" onPress={() => openRecurring(item)} variant="soft" /><PrimaryButton label="Eliminar" onPress={() => removeRecurring(item)} variant="danger" /></View>
          </Card>
        ))}
      </> : null}

      {!loading && !error && accountsSummary ? <>
        <Text style={sharedStyles.sectionTitle}>Tarjetas y préstamos</Text>
        <Card>
          <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Deuda total</Text><Text style={styles.debtValue}>{formatMoney(accountsSummary.total_debt)}</Text></View>
          <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Cupo disponible</Text><Text style={styles.available}>{formatMoney(accountsSummary.total_available_credit)}</Text></View>
          <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Interés mensual estimado</Text><Text style={sharedStyles.body}>{formatMoney(accountsSummary.estimated_monthly_interest)}</Text></View>
        </Card>
        {accountsSummary.accounts.length === 0 ? <LoadState loading={false} error="" empty="No tienes tarjetas ni préstamos registrados." onRetry={() => void load()} /> : accountsSummary.accounts.map((account) => (
          <Card key={account.id}>
            <View style={sharedStyles.between}><Text style={styles.expenseTitle}>{account.name}</Text><Text style={styles.debtValue}>{formatMoney(account.balance)}</Text></View>
            <Text style={sharedStyles.muted}>{account.account_type} · Próximo pago {formatDate(`${account.next_payment_due_date}T12:00:00-05:00`)}</Text>
            {account.available_credit !== null ? <Text style={sharedStyles.body}>Cupo disponible: {formatMoney(account.available_credit)} · Corte: día {account.statement_day}</Text> : null}
            <Text style={sharedStyles.body}>Tasa anual: {account.annual_interest_rate}% · Interés mensual estimado: {formatMoney(account.estimated_monthly_interest)}</Text>
            {account.minimum_payment !== null ? <Text style={sharedStyles.body}>{account.account_type === "Préstamo" ? "Cuota" : "Pago mínimo"}: {formatMoney(account.minimum_payment)}</Text> : null}
            <View style={sharedStyles.actions}><PrimaryButton label="Editar" onPress={() => openAccount(account)} variant="soft" /><PrimaryButton label="Eliminar" onPress={() => removeAccount(account)} variant="danger" /></View>
          </Card>
        ))}
      </> : null}

      {!loading && !error && savingsSummary ? <>
        <Text style={sharedStyles.sectionTitle}>Metas de ahorro</Text>
        <Card style={styles.cream}>
          <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Ahorrado</Text><Text style={styles.cashIncome}>{formatMoney(savingsSummary.total_saved)}</Text></View>
          <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Objetivo total</Text><Text style={styles.budgetValue}>{formatMoney(savingsSummary.total_target)}</Text></View>
          <View style={styles.progress}><View style={[styles.progressFill, { width: `${Math.min(Number(savingsSummary.percentage_complete), 100)}%` }]} /></View>
          <Text style={sharedStyles.muted}>{savingsSummary.percentage_complete}% completado · faltan {formatMoney(savingsSummary.total_remaining)}</Text>
        </Card>
        {savingsSummary.goals.length === 0 ? <LoadState loading={false} error="" empty="Todavía no tienes metas de ahorro." onRetry={() => void load()} /> : savingsSummary.goals.map((goal) => (
          <Card key={goal.id}>
            <View style={sharedStyles.between}><Text style={styles.expenseTitle}>{goal.name}</Text><Text style={styles.incomeAmount}>{goal.percentage_complete}%</Text></View>
            <Text style={sharedStyles.body}>{formatMoney(goal.current_amount)} de {formatMoney(goal.target_amount)}</Text>
            <View style={styles.progress}><View style={[styles.progressFill, { width: `${Math.min(Number(goal.percentage_complete), 100)}%` }]} /></View>
            <Text style={sharedStyles.muted}>{goal.target_date ? `Fecha objetivo: ${formatDate(`${goal.target_date}T12:00:00-05:00`)} · ` : ""}Faltan {formatMoney(goal.remaining_amount)}</Text>
            <View style={sharedStyles.actions}><PrimaryButton label="Aportar" onPress={() => openContribution(goal)} /><PrimaryButton label="Editar" onPress={() => openGoal(goal)} variant="soft" /><PrimaryButton label="Eliminar" onPress={() => removeGoal(goal)} variant="danger" /></View>
          </Card>
        ))}
      </> : null}

      {!loading && !error ? <>
        <Text style={sharedStyles.sectionTitle}>Presupuesto mensual</Text>
        <Card>
          {budget ? <>
            <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Presupuesto</Text><Text style={styles.budgetValue}>{formatMoney(budget.amount)}</Text></View>
            <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Gastado</Text><Text style={sharedStyles.body}>{formatMoney(budget.spent)}</Text></View>
            <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Disponible</Text><Text style={[styles.available, Number(budget.available) < 0 && styles.negative]}>{formatMoney(budget.available)}</Text></View>
            <View style={styles.progress}><View style={[styles.progressFill, { width: `${Math.min(Number(budget.percentage_used), 100)}%` }]} /></View>
            <Text style={sharedStyles.muted}>{budget.percentage_used}% utilizado</Text>
            <View style={sharedStyles.actions}><PrimaryButton label="Editar" onPress={openBudget} variant="soft" /><PrimaryButton label="Eliminar" onPress={removeBudget} variant="danger" /></View>
          </> : <><Text style={sharedStyles.body}>Aún no tienes presupuesto para este mes.</Text><PrimaryButton label="Definir presupuesto" onPress={openBudget} variant="soft" /></>}
        </Card>

        <Text style={sharedStyles.sectionTitle}>Ingresos recientes</Text>
        {incomes.length === 0 ? <LoadState loading={false} error="" empty="Todavía no has registrado ingresos." onRetry={() => void load()} /> : incomes.map((income) => (
          <Card key={income.id}>
            <View style={sharedStyles.between}><Text style={styles.expenseTitle}>{income.description}</Text><Text style={styles.incomeAmount}>{formatMoney(income.amount)}</Text></View>
            <Text style={sharedStyles.muted}>{income.category} · {formatDate(`${income.date}T12:00:00-05:00`)}</Text>
            {income.note ? <Text style={sharedStyles.body}>{income.note}</Text> : null}
            <View style={sharedStyles.actions}><PrimaryButton label="Editar" onPress={() => openIncome(income)} variant="soft" /><PrimaryButton label="Eliminar" onPress={() => removeIncome(income)} variant="danger" /></View>
          </Card>
        ))}

        <Text style={sharedStyles.sectionTitle}>Gastos recientes</Text>
        <Chips values={categoryFilters} selected={categoryFilter} onSelect={setCategoryFilter} />
        <View style={styles.filterDates}><Field label="Desde" value={from} onChangeText={setFrom} placeholder="AAAA-MM-DD" /><Field label="Hasta" value={to} onChangeText={setTo} placeholder="AAAA-MM-DD" /></View>
        <PrimaryButton label="Aplicar rango" onPress={() => void load()} variant="soft" />
        {expenses.length === 0 ? <LoadState loading={false} error="" empty="No hay gastos para estos filtros." onRetry={() => void load()} /> : expenses.map((expense) => (
          <Card key={expense.id}>
            <View style={sharedStyles.between}><Text style={styles.expenseTitle}>{expense.description}</Text><Text style={styles.expenseAmount}>{formatMoney(expense.amount)}</Text></View>
            <Text style={sharedStyles.muted}>{expense.category} · {formatDate(`${expense.date}T12:00:00-05:00`)}</Text>
            {expense.note ? <Text style={sharedStyles.body}>{expense.note}</Text> : null}
            <View style={sharedStyles.actions}><PrimaryButton label="Editar" onPress={() => openExpense(expense)} variant="soft" /><PrimaryButton label="Eliminar" onPress={() => removeExpense(expense)} variant="danger" /></View>
          </Card>
        ))}
      </> : null}

      <FormModal visible={expenseModal} title={editing ? "Editar gasto" : "Registrar gasto"} onClose={() => !saving && setExpenseModal(false)}>
        <Field label="Descripción *" value={description} onChangeText={setDescription} placeholder="Ej. Almuerzo" />
        <Field label="Monto *" value={amount} onChangeText={setAmount} placeholder="0" keyboardType="decimal-pad" />
        <Text style={styles.formLabel}>Categoría</Text><Chips values={categories} selected={category} onSelect={setCategory} />
        <Field label="Fecha *" value={expenseDate} onChangeText={setExpenseDate} placeholder="AAAA-MM-DD" />
        <Field label="Nota" value={note} onChangeText={setNote} placeholder="Opcional" multiline />
        {formError ? <Text style={sharedStyles.error}>{formError}</Text> : null}
        <PrimaryButton label={saving ? "Guardando…" : "Guardar gasto"} onPress={() => void saveExpense()} disabled={saving} />
      </FormModal>

      <FormModal visible={budgetModal} title={budget ? "Editar presupuesto" : "Presupuesto del mes"} onClose={() => !saving && setBudgetModal(false)}>
        <Field label="Monto mensual *" value={budgetAmount} onChangeText={setBudgetAmount} placeholder="1500000" keyboardType="decimal-pad" />
        {formError ? <Text style={sharedStyles.error}>{formError}</Text> : null}
        <PrimaryButton label={saving ? "Guardando…" : "Guardar presupuesto"} onPress={() => void saveBudget()} disabled={saving} />
      </FormModal>

      <FormModal visible={incomeModal} title={editingIncome ? "Editar ingreso" : "Registrar ingreso"} onClose={() => !saving && setIncomeModal(false)}>
        <Field label="Descripción *" value={incomeDescription} onChangeText={setIncomeDescription} placeholder="Ej. Pago de monitoría" />
        <Field label="Monto *" value={incomeAmount} onChangeText={setIncomeAmount} placeholder="0" keyboardType="decimal-pad" />
        <Text style={styles.formLabel}>Categoría</Text><Chips values={incomeCategories} selected={incomeCategory} onSelect={setIncomeCategory} />
        <Field label="Fecha *" value={incomeDate} onChangeText={setIncomeDate} placeholder="AAAA-MM-DD" />
        <Field label="Nota" value={incomeNote} onChangeText={setIncomeNote} placeholder="Opcional" multiline />
        {formError ? <Text style={sharedStyles.error}>{formError}</Text> : null}
        <PrimaryButton label={saving ? "Guardando…" : "Guardar ingreso"} onPress={() => void saveIncome()} disabled={saving} />
      </FormModal>

      <FormModal visible={accountModal} title={editingAccount ? "Editar cuenta" : "Registrar tarjeta o préstamo"} onClose={() => !saving && setAccountModal(false)}>
        <Text style={styles.formLabel}>Tipo</Text><Chips values={accountTypes} selected={accountType} onSelect={setAccountType} />
        <Field label="Nombre *" value={accountName} onChangeText={setAccountName} placeholder="Ej. Tarjeta Nu" />
        <Field label="Deuda actual *" value={accountBalance} onChangeText={setAccountBalance} placeholder="0" keyboardType="decimal-pad" />
        {accountType === "Tarjeta de crédito" ? <><Field label="Cupo total *" value={creditLimit} onChangeText={setCreditLimit} placeholder="0" keyboardType="decimal-pad" /><Field label="Día de corte *" value={statementDay} onChangeText={setStatementDay} placeholder="1 a 31" keyboardType="number-pad" /></> : null}
        <Field label="Día límite de pago *" value={paymentDueDay} onChangeText={setPaymentDueDay} placeholder="1 a 31" keyboardType="number-pad" />
        <Field label="Tasa efectiva anual (%)" value={interestRate} onChangeText={setInterestRate} placeholder="Ej. 24.5" keyboardType="decimal-pad" />
        <Field label={accountType === "Préstamo" ? "Cuota mensual *" : "Pago mínimo *"} value={minimumPayment} onChangeText={setMinimumPayment} placeholder="Necesario si existe deuda" keyboardType="decimal-pad" />
        {formError ? <Text style={sharedStyles.error}>{formError}</Text> : null}
        <PrimaryButton label={saving ? "Guardando…" : "Guardar cuenta"} onPress={() => void saveAccount()} disabled={saving} />
      </FormModal>

      <FormModal visible={goalModal} title={editingGoal ? "Editar meta" : "Crear meta de ahorro"} onClose={() => !saving && setGoalModal(false)}>
        <Field label="Nombre *" value={goalName} onChangeText={setGoalName} placeholder="Ej. Fondo de emergencia" />
        <Field label="Monto objetivo *" value={goalTarget} onChangeText={setGoalTarget} placeholder="0" keyboardType="decimal-pad" />
        <Field label="Ya ahorrado" value={goalCurrent} onChangeText={setGoalCurrent} placeholder="0" keyboardType="decimal-pad" />
        <Field label="Fecha objetivo" value={goalDate} onChangeText={setGoalDate} placeholder="AAAA-MM-DD (opcional)" />
        {formError ? <Text style={sharedStyles.error}>{formError}</Text> : null}
        <PrimaryButton label={saving ? "Guardando…" : "Guardar meta"} onPress={() => void saveGoal()} disabled={saving} />
      </FormModal>

      <FormModal visible={contributionModal} title={`Aportar a ${contributionGoal?.name ?? "la meta"}`} onClose={() => !saving && setContributionModal(false)}>
        <Field label="Monto del aporte *" value={contributionAmount} onChangeText={setContributionAmount} placeholder="0" keyboardType="decimal-pad" />
        {formError ? <Text style={sharedStyles.error}>{formError}</Text> : null}
        <PrimaryButton label={saving ? "Guardando…" : "Registrar aporte"} onPress={() => void saveContribution()} disabled={saving} />
      </FormModal>

      <FormModal visible={recurringModal} title={editingRecurring ? "Editar recurrencia" : "Nuevo movimiento recurrente"} onClose={() => !saving && setRecurringModal(false)}>
        <Text style={styles.formLabel}>Tipo</Text>
        <Chips values={transactionKinds} selected={recurringKind} onSelect={selectRecurringKind} />
        <Field label="Descripción *" value={recurringDescription} onChangeText={setRecurringDescription} placeholder="Ej. Arriendo o salario" />
        <Field label="Monto *" value={recurringAmount} onChangeText={setRecurringAmount} placeholder="0" keyboardType="decimal-pad" />
        <Text style={styles.formLabel}>Categoría</Text>
        {recurringKind === "Ingreso" ? (
          <Chips values={incomeCategories} selected={recurringCategory as IncomeCategory} onSelect={setRecurringCategory} />
        ) : (
          <Chips values={categories} selected={recurringCategory as ExpenseCategory} onSelect={setRecurringCategory} />
        )}
        <Text style={styles.formLabel}>Frecuencia</Text>
        <Chips values={recurrenceFrequencies} selected={recurringFrequency} onSelect={setRecurringFrequency} />
        <Field label="Repetir cada" value={recurringInterval} onChangeText={setRecurringInterval} placeholder="1" keyboardType="number-pad" />
        <Field label="Fecha inicial *" value={recurringStart} onChangeText={setRecurringStart} placeholder="AAAA-MM-DD" />
        <Field label="Fecha final" value={recurringEnd} onChangeText={setRecurringEnd} placeholder="AAAA-MM-DD (opcional)" />
        <Field label="Nota" value={recurringNote} onChangeText={setRecurringNote} placeholder="Opcional" multiline />
        <View style={styles.formSwitch}>
          <Text style={sharedStyles.body}>Incluir en las proyecciones</Text>
          <Switch value={recurringActive} onValueChange={setRecurringActive} trackColor={{ false: colors.border, true: colors.primary }} />
        </View>
        {formError ? <Text style={sharedStyles.error}>{formError}</Text> : null}
        <PrimaryButton label={saving ? "Guardando…" : "Guardar recurrencia"} onPress={() => void saveRecurring()} disabled={saving} />
      </FormModal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  mainActions: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  stats: { flexDirection: "row", gap: 8 },
  stat: { flex: 1, padding: 12, minHeight: 92, justifyContent: "center" },
  pink: { backgroundColor: colors.pinkSoft }, cream: { backgroundColor: colors.cream }, blue: { backgroundColor: colors.blue },
  statLabel: { color: colors.muted, fontSize: 12, fontWeight: "700" },
  statValue: { color: colors.text, fontSize: 14, fontWeight: "900" },
  budgetValue: { color: colors.text, fontSize: 20, fontWeight: "900" },
  available: { color: colors.success, fontSize: 17, fontWeight: "900" }, negative: { color: colors.danger },
  progress: { height: 10, backgroundColor: colors.pinkSoft, borderRadius: 99, overflow: "hidden" },
  progressFill: { height: "100%", backgroundColor: colors.primary },
  filterDates: { flexDirection: "row", gap: 10 },
  expenseTitle: { flex: 1, color: colors.text, fontSize: 16, fontWeight: "800" },
  expenseAmount: { color: colors.primaryDark, fontSize: 16, fontWeight: "900" },
  incomeAmount: { color: colors.success, fontSize: 16, fontWeight: "900" },
  cashIncome: { color: colors.success, fontSize: 16, fontWeight: "900" },
  cashExpense: { color: colors.primaryDark, fontSize: 16, fontWeight: "900" },
  cashNet: { color: colors.success, fontSize: 20, fontWeight: "900" },
  cashDivider: { height: 1, backgroundColor: colors.border, marginVertical: 4 },
  debtValue: { color: colors.danger, fontSize: 17, fontWeight: "900" },
  formLabel: { color: colors.text, fontSize: 13, fontWeight: "700", marginBottom: -8 },
  formSwitch: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  warningCard: { backgroundColor: colors.overdue },
});
