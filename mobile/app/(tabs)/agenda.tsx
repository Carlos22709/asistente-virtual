/** Pantalla para consultar y administrar eventos de agenda. */

import { useCallback, useMemo, useState } from "react";
import { Alert, RefreshControl, StyleSheet, Switch, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
import { Card, Field, FormModal, LoadState, PageHeader, PrimaryButton, Screen, sharedStyles } from "@/components/ui";
import { colors } from "@/constants/theme";
import { eventService } from "@/services/events";
import { cancelReminder, getActiveReminderIds, hasReminder, replaceReminder } from "@/services/notifications";
import { EventInput, EventItem } from "@/types";
import { formatDate, formatDateTime, isoToLocalInput, localInputToIso } from "@/utils/format";

export default function AgendaScreen() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [reminderIds, setReminderIds] = useState<Set<number>>(new Set());
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<EventItem | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [location, setLocation] = useState("");
  const [reminder, setReminder] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const load = useCallback(async (pull = false) => {
    pull ? setRefreshing(true) : setLoading(true); setError("");
    try {
      const fromIso = from ? localInputToIso(`${from}T00:00`) ?? undefined : undefined;
      const toIso = to ? localInputToIso(`${to}T23:59`) ?? undefined : undefined;
      const items = await eventService.list({ upcoming: !from && !to, date_from: fromIso, date_to: toIso });
      setEvents(items);
      setReminderIds(await getActiveReminderIds("event", items.map((event) => event.id)));
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudo cargar la agenda."); }
    finally { setLoading(false); setRefreshing(false); }
  }, [from, to]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  const grouped = useMemo(() => events.reduce<Record<string, EventItem[]>>((groups, event) => {
    const key = formatDate(event.start_datetime);
    (groups[key] ??= []).push(event);
    return groups;
  }, {}), [events]);

  const openForm = async (event?: EventItem) => {
    setNotice("");
    setEditing(event ?? null); setTitle(event?.title ?? ""); setDescription(event?.description ?? "");
    setStart(isoToLocalInput(event?.start_datetime ?? null)); setEnd(isoToLocalInput(event?.end_datetime ?? null));
    setLocation(event?.location ?? ""); setReminder(event ? await hasReminder("event", event.id) : false); setFormError(""); setModal(true);
  };

  const save = async () => {
    const startIso = localInputToIso(start); const endIso = end ? localInputToIso(end) : null;
    if (!title.trim()) return setFormError("Escribe un título para el evento.");
    if (!startIso) return setFormError("Escribe una fecha y hora inicial válida.");
    if (end && !endIso) return setFormError("La fecha final no es válida.");
    if (endIso && new Date(endIso) < new Date(startIso)) return setFormError("La fecha final no puede ser anterior a la inicial.");
    const payload: EventInput = { title: title.trim(), description: description.trim() || null, start_datetime: startIso, end_datetime: endIso, location: location.trim() || null };
    setSaving(true); setFormError("");
    try {
      const saved = editing ? await eventService.update(editing.id, payload) : await eventService.create(payload);
      if (reminder) {
        const granted = await replaceReminder("event", saved.id, "Próximo evento", title.trim(), new Date(startIso));
        if (!granted) Alert.alert("Sin recordatorio", "El evento se guardó, pero no se pudo programar la notificación.");
      } else await cancelReminder("event", saved.id);
      setNotice(editing ? "Evento actualizado." : "Evento creado.");
      setModal(false); await load();
    } catch (err) { setFormError(err instanceof Error ? err.message : "No se pudo guardar el evento."); }
    finally { setSaving(false); }
  };

  const remove = (event: EventItem) => Alert.alert("Eliminar evento", `¿Seguro que quieres eliminar “${event.title}”?`, [
    { text: "Cancelar", style: "cancel" },
    { text: "Eliminar", style: "destructive", onPress: async () => {
      try { await eventService.remove(event.id); await cancelReminder("event", event.id); setNotice("Evento eliminado."); await load(); }
      catch (err) { Alert.alert("No fue posible", err instanceof Error ? err.message : "Intenta de nuevo."); }
    } },
  ]);

  return (
    <Screen refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void load(true)} tintColor={colors.primary} />}>
      <PageHeader eyebrow="Tu tiempo, visible" title="Agenda" subtitle="Próximos eventos agrupados por día." />
      <PrimaryButton label="＋ Nuevo evento" onPress={() => void openForm()} />
      {notice ? <Text style={sharedStyles.success}>{notice}</Text> : null}
      <Card style={styles.filters}>
        <Text style={styles.filterTitle}>Filtrar por rango</Text>
        <View style={styles.filterRow}><Field label="Desde" value={from} onChangeText={setFrom} placeholder="AAAA-MM-DD" /><Field label="Hasta" value={to} onChangeText={setTo} placeholder="AAAA-MM-DD" /></View>
        <View style={sharedStyles.actions}><PrimaryButton label="Aplicar" onPress={() => void load()} variant="soft" /><PrimaryButton label="Limpiar" onPress={() => { setFrom(""); setTo(""); }} variant="soft" /></View>
      </Card>
      <LoadState loading={loading} error={error} empty={!loading && !error && events.length === 0 ? "Tu agenda está despejada. ✦" : undefined} onRetry={() => void load()} />
      {!loading && !error && Object.entries(grouped).map(([day, items]) => (
        <View key={day} style={styles.group}>
          <Text style={styles.day}>{day}</Text>
          {items.map((event) => (
            <Card key={event.id}>
              <View style={sharedStyles.between}><Text style={styles.eventTitle}>{event.title}</Text><Text style={styles.star}>✦</Text></View>
              <Text style={styles.time}>{formatDateTime(event.start_datetime)}{event.end_datetime ? ` – ${formatDateTime(event.end_datetime)}` : ""}</Text>
              {event.location ? <Text style={sharedStyles.muted}>Ubicación: {event.location}</Text> : null}
              {event.description ? <Text style={sharedStyles.body}>{event.description}</Text> : null}
              {reminderIds.has(event.id) ? <Text style={styles.reminderActive}>Recordatorio activo</Text> : null}
              <View style={sharedStyles.actions}><PrimaryButton label="Editar" onPress={() => void openForm(event)} variant="soft" /><PrimaryButton label="Eliminar" onPress={() => remove(event)} variant="danger" /></View>
            </Card>
          ))}
        </View>
      ))}

      <FormModal visible={modal} title={editing ? "Editar evento" : "Nuevo evento"} onClose={() => !saving && setModal(false)}>
        <Field label="Título *" value={title} onChangeText={setTitle} placeholder="Ej. Gestión de Proyectos" />
        <Field label="Descripción" value={description} onChangeText={setDescription} placeholder="Detalles opcionales" multiline />
        <Field label="Inicio *" value={start} onChangeText={setStart} placeholder="AAAA-MM-DDTHH:mm" autoCapitalize="none" />
        <Field label="Final" value={end} onChangeText={setEnd} placeholder="AAAA-MM-DDTHH:mm" autoCapitalize="none" />
        <Field label="Ubicación" value={location} onChangeText={setLocation} placeholder="Opcional" />
        {start ? <View style={sharedStyles.between}><Text style={sharedStyles.body}>Programar recordatorio local</Text><Switch value={reminder} onValueChange={setReminder} trackColor={{ true: colors.primary }} /></View> : null}
        {formError ? <Text style={sharedStyles.error}>{formError}</Text> : null}
        <PrimaryButton label={saving ? "Guardando…" : "Guardar evento"} onPress={() => void save()} disabled={saving} />
      </FormModal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  filters: { backgroundColor: colors.blue },
  filterTitle: { color: colors.text, fontWeight: "800", fontSize: 15 },
  filterRow: { flexDirection: "row", gap: 10 },
  group: { gap: 10 },
  day: { color: colors.primaryDark, fontSize: 16, fontWeight: "900", textTransform: "capitalize", marginTop: 5 },
  eventTitle: { flex: 1, color: colors.text, fontSize: 17, fontWeight: "900" },
  time: { color: colors.primaryDark, fontWeight: "700", fontSize: 13 },
  star: { color: colors.yellow, fontSize: 20 },
  reminderActive: { color: colors.success, fontSize: 12, fontWeight: "800" },
});
