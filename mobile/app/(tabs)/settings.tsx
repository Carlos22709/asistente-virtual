/** Configuracion de conexion, diagnostico y respaldo de datos. */

import { useEffect, useState } from "react";
import * as DocumentPicker from "expo-document-picker";
import * as FileSystem from "expo-file-system/legacy";
import * as Notifications from "expo-notifications";
import * as Sharing from "expo-sharing";
import { Alert, RefreshControl, StyleSheet, Text, View } from "react-native";

import { Card, Field, PageHeader, PrimaryButton, Screen, sharedStyles } from "@/components/ui";
import { colors } from "@/constants/theme";
import {
  defaultApiUrl,
  getApiConfiguration,
  saveApiConfiguration,
} from "@/services/configuration";
import { systemService } from "@/services/system";
import { SystemStatus } from "@/types";
import { formatDateTime } from "@/utils/format";

const componentNames: Record<string, string> = {
  database: "Base de datos",
  ollama: "Ollama",
  gmail: "Gmail",
  bank_webhook: "Automatización bancaria",
};

export default function SettingsScreen() {
  const [apiUrl, setApiUrl] = useState(defaultApiUrl());
  const [apiToken, setApiToken] = useState("");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [notificationStatus, setNotificationStatus] = useState("Sin comprobar");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [configuration, permission] = await Promise.all([
        getApiConfiguration(),
        Notifications.getPermissionsAsync(),
      ]);
      setApiUrl(configuration.apiUrl);
      setApiToken(configuration.apiToken);
      setNotificationStatus(permission.granted ? "Permitidas" : "Sin permiso");
      setStatus(await systemService.status());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "No fue posible consultar el sistema.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const saveAndTest = async () => {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await saveApiConfiguration({ apiUrl, apiToken });
      const result = await systemService.status();
      setStatus(result);
      setMessage("Configuración guardada y conexión verificada.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "No fue posible guardar la configuración.");
    } finally {
      setSaving(false);
    }
  };

  const requestNotificationPermission = async () => {
    const permission = await Notifications.requestPermissionsAsync();
    setNotificationStatus(permission.granted ? "Permitidas" : "Sin permiso");
  };

  const exportBackup = async () => {
    setSaving(true);
    setError("");
    try {
      const backup = await systemService.backup();
      if (!FileSystem.cacheDirectory) throw new Error("El dispositivo no ofrece almacenamiento temporal.");
      const path = FileSystem.cacheDirectory + "kirby-backup-" + backup.exported_at.slice(0, 10) + ".json";
      await FileSystem.writeAsStringAsync(path, JSON.stringify(backup, null, 2));
      if (!(await Sharing.isAvailableAsync())) throw new Error("No es posible compartir archivos en este dispositivo.");
      await Sharing.shareAsync(path, { mimeType: "application/json", dialogTitle: "Guardar copia de Kirby" });
      setMessage("Copia exportada correctamente.");
    } catch (backupError) {
      setError(backupError instanceof Error ? backupError.message : "No fue posible exportar la copia.");
    } finally {
      setSaving(false);
    }
  };

  const chooseBackup = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: "application/json",
      copyToCacheDirectory: true,
    });
    if (result.canceled) return;
    Alert.alert(
      "Restaurar copia",
      "Esta operación reemplazará los datos actuales por el contenido de la copia seleccionada.",
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Restaurar",
          style: "destructive",
          onPress: () => void restoreBackup(result.assets[0].uri),
        },
      ],
    );
  };

  const restoreBackup = async (uri: string) => {
    setSaving(true);
    setError("");
    try {
      const content = await FileSystem.readAsStringAsync(uri);
      const backup = JSON.parse(content);
      const result = await systemService.restore(backup, true);
      setMessage("Copia restaurada: " + result.restored_rows + " registros.");
      await load();
    } catch (restoreError) {
      setError(restoreError instanceof Error ? restoreError.message : "No fue posible restaurar la copia.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Screen
      refreshControl={<RefreshControl refreshing={loading} onRefresh={() => void load()} />}
    >
      <PageHeader
        eyebrow="Configuración"
        title="Estado de Kirby"
        subtitle="Conecta el teléfono y comprueba cada integración desde un solo lugar."
      />

      <Card>
        <Text style={sharedStyles.sectionTitle}>Conexión con el servidor</Text>
        <Field
          label="URL de la API"
          value={apiUrl}
          onChangeText={setApiUrl}
          autoCapitalize="none"
          autoCorrect={false}
          placeholder="http://100.x.x.x:3000"
        />
        <Field
          label="Token personal (opcional)"
          value={apiToken}
          onChangeText={setApiToken}
          autoCapitalize="none"
          autoCorrect={false}
          secureTextEntry
          placeholder="Debe coincidir con APP_API_TOKEN"
        />
        {message ? <Text style={sharedStyles.success}>{message}</Text> : null}
        {error ? <Text style={sharedStyles.error}>{error}</Text> : null}
        <PrimaryButton
          label={saving ? "Comprobando…" : "Guardar y comprobar"}
          onPress={() => void saveAndTest()}
          disabled={saving}
        />
      </Card>

      <Card>
        <View style={sharedStyles.between}>
          <Text style={sharedStyles.sectionTitle}>Notificaciones</Text>
          <Text style={notificationStatus === "Permitidas" ? styles.ready : styles.warning}>
            {notificationStatus}
          </Text>
        </View>
        <Text style={sharedStyles.muted}>
          Se usan para tareas, eventos y próximos pagos sin necesitar un servidor push.
        </Text>
        {notificationStatus !== "Permitidas" ? (
          <PrimaryButton
            label="Permitir notificaciones"
            onPress={() => void requestNotificationPermission()}
            variant="soft"
          />
        ) : null}
      </Card>

      <Card>
        <Text style={sharedStyles.sectionTitle}>Copia de seguridad</Text>
        <Text style={sharedStyles.muted}>
          Exporta tareas, agenda, finanzas, automatizaciones y metas en un archivo JSON. También puedes restaurar una copia completa.
        </Text>
        <View style={sharedStyles.actions}>
          <PrimaryButton label="Exportar copia" onPress={() => void exportBackup()} disabled={saving} variant="soft" />
          <PrimaryButton label="Restaurar copia" onPress={() => void chooseBackup()} disabled={saving} variant="danger" />
        </View>
      </Card>

      {status ? (
        <>
          <Card style={status.status === "ready" ? styles.readyCard : styles.warningCard}>
            <View style={sharedStyles.between}>
              <Text style={sharedStyles.sectionTitle}>
                {status.status === "ready" ? "Sistema listo" : "Sistema incompleto"}
              </Text>
              <Text style={status.status === "ready" ? styles.ready : styles.warning}>
                {status.database_provider}
              </Text>
            </View>
            <Text style={sharedStyles.muted}>
              Revisado {formatDateTime(status.checked_at)} · protección de API{" "}
              {status.api_auth_enabled ? "activa" : "desactivada"}
            </Text>
          </Card>
          {Object.entries(status.components).map(([name, component]) => (
            <Card key={name}>
              <View style={sharedStyles.between}>
                <Text style={styles.componentTitle}>{componentNames[name] ?? name}</Text>
                <Text style={component.status === "ready" ? styles.ready : styles.warning}>
                  {component.status === "ready" ? "Listo" : component.status === "missing" ? "Falta configurar" : "Error"}
                </Text>
              </View>
              <Text style={sharedStyles.muted}>{component.detail}</Text>
            </Card>
          ))}
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  componentTitle: { color: colors.text, fontSize: 16, fontWeight: "800" },
  ready: { color: colors.success, fontWeight: "800" },
  warning: { color: colors.danger, fontWeight: "800" },
  readyCard: { backgroundColor: "#EFFBF6" },
  warningCard: { backgroundColor: colors.overdue },
});
