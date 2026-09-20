/** Componentes visuales reutilizables y estilos compartidos. */

import { PropsWithChildren, ReactElement } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  RefreshControlProps,
  ScrollView,
  StyleProp,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
  ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, shadows } from "@/constants/theme";

export function Screen({ children, refreshControl }: PropsWithChildren<{ refreshControl?: ReactElement<RefreshControlProps> }>) {
  return (
    <SafeAreaView style={styles.safe} edges={["top", "left", "right"]}>
      <ScrollView
        contentContainerStyle={styles.screen}
        keyboardShouldPersistTaps="handled"
        refreshControl={refreshControl}
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

export function PageHeader({ eyebrow, title, subtitle }: { eyebrow?: string; title: string; subtitle?: string }) {
  return (
    <View style={styles.header}>
      {eyebrow ? <Text style={styles.eyebrow}>{eyebrow}</Text> : null}
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

export function Card({ children, style }: PropsWithChildren<{ style?: StyleProp<ViewStyle> }>) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function PrimaryButton({
  label,
  onPress,
  disabled,
  variant = "primary",
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  variant?: "primary" | "soft" | "danger";
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        variant === "soft" && styles.buttonSoft,
        variant === "danger" && styles.buttonDanger,
        (pressed || disabled) && styles.buttonPressed,
      ]}
    >
      <Text style={[styles.buttonText, variant === "soft" && styles.buttonSoftText]}>{label}</Text>
    </Pressable>
  );
}

export function Field({ label, ...props }: TextInputProps & { label: string }) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput placeholderTextColor="#A997A7" style={styles.input} {...props} />
    </View>
  );
}

export function Chips<T extends string>({
  values,
  selected,
  onSelect,
}: {
  values: readonly T[];
  selected: T;
  onSelect: (value: T) => void;
}) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
      {values.map((value) => (
        <Pressable
          key={value}
          onPress={() => onSelect(value)}
          style={[styles.chip, selected === value && styles.chipSelected]}
        >
          <Text style={[styles.chipText, selected === value && styles.chipTextSelected]}>{value}</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

export function FormModal({
  visible,
  title,
  children,
  onClose,
}: PropsWithChildren<{ visible: boolean; title: string; onClose: () => void }>) {
  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalSafe}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>{title}</Text>
          <Pressable onPress={onClose}><Text style={styles.close}>Cerrar</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalContent} keyboardShouldPersistTaps="handled">
          {children}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

export function LoadState({ loading, error, empty, onRetry }: { loading: boolean; error: string; empty?: string; onRetry: () => void }) {
  if (loading) return <ActivityIndicator size="large" color={colors.primary} style={{ margin: 30 }} />;
  if (error) return <Card><Text style={styles.error}>{error}</Text><PrimaryButton label="Reintentar" onPress={onRetry} variant="soft" /></Card>;
  if (empty) return <Card style={styles.empty}><Text style={styles.star}>✦</Text><Text style={styles.emptyText}>{empty}</Text></Card>;
  return null;
}

export const sharedStyles = StyleSheet.create({
  sectionTitle: { color: colors.text, fontSize: 18, fontWeight: "800", marginTop: 6 },
  row: { flexDirection: "row", alignItems: "center", gap: 10 },
  between: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10 },
  body: { color: colors.text, fontSize: 15, lineHeight: 21 },
  muted: { color: colors.muted, fontSize: 13, lineHeight: 18 },
  actions: { flexDirection: "row", gap: 8, marginTop: 12, flexWrap: "wrap" },
  error: { color: colors.danger, marginBottom: 10, fontWeight: "600" },
  success: { color: colors.success, marginBottom: 10, fontWeight: "600" },
});

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  screen: { padding: 20, paddingBottom: 36, gap: 14 },
  header: { marginBottom: 4 },
  eyebrow: { color: colors.primaryDark, fontWeight: "800", fontSize: 13, letterSpacing: 1, textTransform: "uppercase" },
  title: { color: colors.text, fontSize: 30, lineHeight: 36, fontWeight: "900", marginTop: 4 },
  subtitle: { color: colors.muted, fontSize: 15, lineHeight: 21, marginTop: 5 },
  card: { backgroundColor: colors.surface, borderRadius: 22, borderWidth: 1, borderColor: colors.border, padding: 17, gap: 9, ...shadows },
  button: { minHeight: 44, paddingHorizontal: 17, borderRadius: 15, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  buttonSoft: { backgroundColor: colors.pinkSoft },
  buttonDanger: { backgroundColor: colors.danger },
  buttonPressed: { opacity: 0.55 },
  buttonText: { color: "white", fontSize: 14, fontWeight: "800" },
  buttonSoftText: { color: colors.primaryDark },
  fieldWrap: { gap: 6 },
  fieldLabel: { color: colors.text, fontSize: 13, fontWeight: "700" },
  input: { minHeight: 48, borderWidth: 1, borderColor: colors.border, borderRadius: 14, backgroundColor: "white", paddingHorizontal: 14, paddingVertical: 10, color: colors.text, fontSize: 15 },
  chips: { gap: 8, paddingVertical: 3 },
  chip: { paddingHorizontal: 14, paddingVertical: 9, borderRadius: 999, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  chipSelected: { backgroundColor: colors.primary },
  chipText: { color: colors.muted, fontWeight: "700" },
  chipTextSelected: { color: "white" },
  modalSafe: { flex: 1, backgroundColor: colors.background },
  modalHeader: { padding: 20, flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: colors.border },
  modalTitle: { color: colors.text, fontSize: 21, fontWeight: "900" },
  close: { color: colors.primaryDark, fontWeight: "800", fontSize: 15 },
  modalContent: { padding: 20, gap: 15, paddingBottom: 50 },
  error: { color: colors.danger, marginBottom: 12 },
  empty: { alignItems: "center", paddingVertical: 30 },
  star: { color: colors.yellow, fontSize: 30 },
  emptyText: { color: colors.muted, textAlign: "center", fontSize: 15 },
});
