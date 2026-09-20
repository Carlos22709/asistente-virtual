/** Contenedor raiz que inicializa notificaciones y navegacion. */

import { useEffect } from "react";
import { Stack, useRouter } from "expo-router";
import * as Notifications from "expo-notifications";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { financialAccountService } from "@/services/financialAccounts";
import { incomeService } from "@/services/incomes";
import { configureNotifications, syncFinancialReminders } from "@/services/notifications";

export default function RootLayout() {
  const router = useRouter();

  useEffect(() => {
    configureNotifications()
      .then(async () => {
        const [accounts, cashFlow] = await Promise.all([
          financialAccountService.summary(),
          incomeService.cashFlow(),
        ]);
        await syncFinancialReminders(accounts.accounts, cashFlow);
      })
      .catch(() => undefined);

    const subscription = Notifications.addNotificationResponseReceivedListener((response) => {
      const entity = response.notification.request.content.data?.entity;
      if (entity === "task") router.push("/(tabs)/tasks");
      else if (entity === "event") router.push("/(tabs)/agenda");
      else if (entity === "financial-account" || entity === "cash-flow") {
        router.push("/(tabs)/finances");
      }
    });
    return () => subscription.remove();
  }, [router]);
  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </SafeAreaProvider>
  );
}
