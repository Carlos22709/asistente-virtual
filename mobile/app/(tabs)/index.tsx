/** Inicio con indicadores consolidados de secretaria y finanzas. */

import { useCallback, useState } from "react";
import { RefreshControl, StyleSheet, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
import { Card, LoadState, PageHeader, Screen, sharedStyles } from "@/components/ui";
import { colors } from "@/constants/theme";
import { dashboardService } from "@/services/dashboard";
import { DashboardSummary } from "@/types";
import { formatDateTime, formatMoney } from "@/utils/format";

function greeting() {
  const hour = Number(new Intl.DateTimeFormat("es-CO", { hour: "2-digit", hourCycle: "h23", timeZone: "America/Bogota" }).format(new Date()));
  if (hour < 12) return "Buenos días";
  if (hour < 18) return "Buenas tardes";
  return "Buenas noches";
}

export default function HomeScreen() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (pull = false) => {
    pull ? setRefreshing(true) : setLoading(true);
    setError("");
    try { setData(await dashboardService.summary()); }
    catch (err) { setError(err instanceof Error ? err.message : "No fue posible cargar el resumen."); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  return (
    <Screen refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void load(true)} tintColor={colors.primary} />}>
      <PageHeader eyebrow="Tu espacio personal" title={`${greeting()}, Carlitos ✦`} subtitle="Un vistazo tranquilo a lo importante de hoy." />
      <LoadState loading={loading} error={error} onRetry={() => void load()} />
      {data ? (
        <>
          <View style={styles.stats}>
            <Card style={[styles.stat, styles.pink]}><Text style={styles.number}>{data.pending_tasks}</Text><Text style={styles.label}>tareas pendientes</Text></Card>
            <Card style={[styles.stat, styles.cream]}><Text style={styles.money}>{formatMoney(data.today_spent)}</Text><Text style={styles.label}>gastado hoy</Text></Card>
          </View>

          <Text style={sharedStyles.sectionTitle}>Próximo en tu día</Text>
          <Card>
            {data.upcoming_tasks[0] ? (
              <><Text style={styles.kicker}>PRÓXIMA TAREA</Text><Text style={styles.cardTitle}>{data.upcoming_tasks[0].title}</Text><Text style={sharedStyles.muted}>{data.upcoming_tasks[0].due_date ? formatDateTime(data.upcoming_tasks[0].due_date) : "Sin fecha límite"} · Prioridad {data.upcoming_tasks[0].priority.toLowerCase()}</Text></>
            ) : <Text style={sharedStyles.muted}>No tienes entregas próximas.</Text>}
            <View style={styles.divider} />
            {data.next_event ? (
              <><Text style={styles.kicker}>PRÓXIMO EVENTO</Text><Text style={styles.cardTitle}>{data.next_event.title}</Text><Text style={sharedStyles.muted}>{formatDateTime(data.next_event.start_datetime)}{data.next_event.location ? ` · ${data.next_event.location}` : ""}</Text></>
            ) : <Text style={sharedStyles.muted}>Tu agenda está despejada.</Text>}
          </Card>

          <Text style={sharedStyles.sectionTitle}>Finanzas del mes</Text>
          <Card style={styles.blue}>
            <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Gastado esta semana</Text><Text style={styles.value}>{formatMoney(data.week_spent)}</Text></View>
            <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Ingresos del mes</Text><Text style={styles.value}>{formatMoney(data.month_income)}</Text></View>
            <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Flujo neto del mes</Text><Text style={[styles.value, Number(data.month_cash_flow) < 0 && styles.negative]}>{formatMoney(data.month_cash_flow)}</Text></View>
            <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Obligaciones pendientes</Text><Text style={styles.value}>{formatMoney(data.month_projected_obligations)}</Text></View>
            <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Disponible proyectado</Text><Text style={[styles.value, Number(data.month_projected_available) < 0 && styles.negative]}>{formatMoney(data.month_projected_available)}</Text></View>
            {data.unconfigured_obligations_count > 0 ? <Text style={sharedStyles.error}>{data.unconfigured_obligations_count} cuenta(s) sin cuota no están incluidas en esta proyección.</Text> : null}
            {data.current_budget ? (
              <>
                <View style={sharedStyles.between}><Text style={sharedStyles.muted}>Presupuesto</Text><Text style={styles.value}>{formatMoney(data.current_budget.amount)}</Text></View>
                <View style={styles.progress}><View style={[styles.progressFill, { width: `${Math.min(Number(data.current_budget.percentage_used), 100)}%` }]} /></View>
                <Text style={sharedStyles.muted}>{data.current_budget.percentage_used}% utilizado · {formatMoney(data.current_budget.available)} disponible</Text>
              </>
            ) : <Text style={sharedStyles.muted}>Aún no has definido el presupuesto de este mes.</Text>}
          </Card>
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  stats: { flexDirection: "row", gap: 12 },
  stat: { flex: 1, minHeight: 120, justifyContent: "center" },
  pink: { backgroundColor: colors.pinkSoft },
  cream: { backgroundColor: colors.cream },
  blue: { backgroundColor: colors.blue },
  number: { color: colors.primaryDark, fontSize: 34, fontWeight: "900" },
  money: { color: colors.text, fontSize: 20, fontWeight: "900" },
  label: { color: colors.muted, fontSize: 13, lineHeight: 18 },
  kicker: { color: colors.primaryDark, fontWeight: "900", fontSize: 11, letterSpacing: 1 },
  cardTitle: { color: colors.text, fontWeight: "800", fontSize: 17 },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: 6 },
  value: { color: colors.text, fontWeight: "900", fontSize: 16 },
  negative: { color: colors.danger },
  progress: { height: 10, backgroundColor: "white", borderRadius: 99, overflow: "hidden", marginTop: 3 },
  progressFill: { height: "100%", backgroundColor: colors.primary, borderRadius: 99 },
});
