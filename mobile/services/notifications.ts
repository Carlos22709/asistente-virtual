/** Programa y sincroniza recordatorios locales de tareas, eventos y pagos. */

import { Platform } from "react-native";
import * as Notifications from "expo-notifications";
import AsyncStorage from "@react-native-async-storage/async-storage";

import { CashFlowSummary, FinancialAccount } from "@/types";

export type ReminderEntity = "task" | "event" | "financial-account" | "cash-flow";

function reminderKey(entity: ReminderEntity, id: number): string {
  return `kirby:reminder:${entity}:${id}`;
}

export async function configureNotifications(): Promise<void> {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: false,
      shouldSetBadge: false,
    }),
  });
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("recordatorios", {
      name: "Recordatorios",
      importance: Notifications.AndroidImportance.DEFAULT,
    });
  }
}

export async function hasReminder(entity: ReminderEntity, id: number): Promise<boolean> {
  return (await getActiveReminderIds(entity, [id])).has(id);
}

export async function getActiveReminderIds(
  entity: ReminderEntity,
  entityIds: number[],
): Promise<Set<number>> {
  // Cruza identificadores persistidos con los que el sistema aun tiene programados.
  if (entityIds.length === 0) return new Set();
  const scheduled = await Notifications.getAllScheduledNotificationsAsync();
  const scheduledIds = new Set(scheduled.map((item) => item.identifier));
  const keys = entityIds.map((id) => reminderKey(entity, id));
  const stored = await AsyncStorage.multiGet(keys);
  const active = new Set<number>();
  const staleKeys: string[] = [];
  stored.forEach(([key, notificationId], index) => {
    if (notificationId && scheduledIds.has(notificationId)) active.add(entityIds[index]);
    else if (notificationId) staleKeys.push(key);
  });
  if (staleKeys.length > 0) await AsyncStorage.multiRemove(staleKeys);
  return active;
}

export async function cancelReminder(entity: ReminderEntity, id: number): Promise<void> {
  const key = reminderKey(entity, id);
  const notificationId = await AsyncStorage.getItem(key);
  if (notificationId) {
    try {
      await Notifications.cancelScheduledNotificationAsync(notificationId);
    } catch {
      // Puede que el sistema ya haya entregado o eliminado la notificación.
    }
  }
  await AsyncStorage.removeItem(key);
}

export async function replaceReminder(
  entity: ReminderEntity,
  id: number,
  title: string,
  body: string,
  date: Date,
): Promise<boolean> {
  await cancelReminder(entity, id);
  if (date.getTime() <= Date.now()) return false;
  const current = await Notifications.getPermissionsAsync();
  const permission = current.granted ? current : await Notifications.requestPermissionsAsync();
  if (!permission.granted) return false;
  try {
    const notificationId = await Notifications.scheduleNotificationAsync({
      content: { title, body, data: { entity, entityId: id } },
      trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date },
    });
    await AsyncStorage.setItem(reminderKey(entity, id), notificationId);
    return true;
  } catch {
    return false;
  }
}

function paymentReminderDate(value: string): Date {
  // El aviso se programa un dia antes; fechas vencidas se muestran de inmediato.
  const due = new Date(value + "T09:00:00-05:00");
  due.setDate(due.getDate() - 1);
  if (due.getTime() <= Date.now()) return new Date(Date.now() + 60_000);
  return due;
}

export async function syncFinancialReminders(
  accounts: FinancialAccount[],
  cashFlow: CashFlowSummary,
): Promise<void> {
  /** Sincroniza pagos pendientes y crea una alerta si el flujo sera negativo. */

  const permission = await Notifications.getPermissionsAsync();
  if (!permission.granted) return;

  await Promise.all(
    accounts
      .filter((account) => Number(account.balance) > 0)
      .map((account) =>
        replaceReminder(
          "financial-account",
          account.id,
          "Pago próximo: " + account.name,
          "Tienes un pago programado por " + (account.minimum_payment ?? "un valor pendiente de configurar") + " COP.",
          paymentReminderDate(account.next_payment_due_date),
        ),
      ),
  );

  const period = cashFlow.projection_end_date.replaceAll("-", "");
  const alertId = Number(period);
  if (Number(cashFlow.projected_available) < 0) {
    await replaceReminder(
      "cash-flow",
      alertId,
      "Alerta de flujo de caja",
      "Tu disponible proyectado para este mes es negativo. Revisa pagos y gastos recurrentes.",
      new Date(Date.now() + 60_000),
    );
  } else {
    await cancelReminder("cash-flow", alertId);
  }
}
