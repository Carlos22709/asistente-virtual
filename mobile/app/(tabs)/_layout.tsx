/** Navegacion inferior entre los modulos principales de la aplicacion. */

import { Tabs } from "expo-router";
import { ColorValue, StyleSheet, Text } from "react-native";
import { colors } from "@/constants/theme";

const icon = (symbol: string, color: ColorValue) => <Text style={[styles.icon, { color }]}>{symbol}</Text>;

export default function TabLayout() {
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: colors.primaryDark,
      tabBarInactiveTintColor: colors.muted,
      tabBarStyle: styles.bar,
      tabBarLabelStyle: styles.label,
    }}>
      <Tabs.Screen name="index" options={{ title: "Inicio", tabBarIcon: ({ color }) => icon("⌂", color) }} />
      <Tabs.Screen name="tasks" options={{ title: "Tareas", tabBarIcon: ({ color }) => icon("✓", color) }} />
      <Tabs.Screen name="finances" options={{ title: "Finanzas", tabBarIcon: ({ color }) => icon("$", color) }} />
      <Tabs.Screen name="agenda" options={{ title: "Agenda", tabBarIcon: ({ color }) => icon("◇", color) }} />
      <Tabs.Screen name="assistant" options={{ title: "Asistente", tabBarIcon: ({ color }) => icon("✦", color) }} />
      <Tabs.Screen name="settings" options={{ title: "Ajustes", tabBarIcon: ({ color }) => icon("⚙", color) }} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  bar: { height: 68, paddingTop: 7, paddingBottom: 9, borderTopColor: colors.border, backgroundColor: colors.surface },
  label: { fontSize: 11, fontWeight: "700" },
  icon: { fontSize: 22, fontWeight: "900" },
});
