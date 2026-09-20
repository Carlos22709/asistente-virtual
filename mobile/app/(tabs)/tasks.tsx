/** Pantalla para crear, filtrar y actualizar tareas personales. */

import { useCallback, useState } from "react";
import { Alert, RefreshControl, StyleSheet, Switch, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
import { Card, Chips, Field, FormModal, LoadState, PageHeader, PrimaryButton, Screen, sharedStyles } from "@/components/ui";
import { colors } from "@/constants/theme";
import { cancelReminder, getActiveReminderIds, hasReminder, replaceReminder } from "@/services/notifications";
import { taskService } from "@/services/tasks";
import { Task, TaskInput, TaskPriority, TaskStatus } from "@/types";
import { formatDateTime, isoToLocalInput, localInputToIso } from "@/utils/format";

const filters = ["Todas", "Pendiente", "En progreso", "Completada"] as const;
const priorities = ["Baja", "Media", "Alta"] as const;

export default function TasksScreen() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [reminderIds, setReminderIds] = useState<Set<number>>(new Set());
  const [filter, setFilter] = useState<(typeof filters)[number]>("Pendiente");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<Task | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [due, setDue] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("Media");
  const [reminder, setReminder] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const load = useCallback(async (pull = false) => {
    pull ? setRefreshing(true) : setLoading(true);
    setError("");
    try {
      const taskStatus = filter === "Todas" ? undefined : filter;
      const items = await taskService.list({ task_status: taskStatus });
      setTasks(items);
      setReminderIds(await getActiveReminderIds("task", items.map((task) => task.id)));
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudieron cargar las tareas."); }
    finally { setLoading(false); setRefreshing(false); }
  }, [filter]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  const openForm = async (task?: Task) => {
    setNotice("");
    setEditing(task ?? null);
    setTitle(task?.title ?? "");
    setDescription(task?.description ?? "");
    setDue(isoToLocalInput(task?.due_date ?? null));
    setPriority(task?.priority ?? "Media");
    setReminder(task ? await hasReminder("task", task.id) : false);
    setFormError("");
    setModal(true);
  };

  const save = async () => {
    if (!title.trim()) return setFormError("Escribe un título para la tarea.");
    const dueIso = due ? localInputToIso(due) : null;
    if (due && !dueIso) return setFormError("Usa una fecha válida, por ejemplo 2026-09-10T15:00.");
    setSaving(true); setFormError("");
    const payload: TaskInput = { title: title.trim(), description: description.trim() || null, due_date: dueIso, priority, status: editing?.status ?? "Pendiente" };
    try {
      const saved = editing ? await taskService.update(editing.id, payload) : await taskService.create(payload);
      if (reminder && dueIso && saved.status !== "Completada") {
        const granted = await replaceReminder("task", saved.id, "Tarea pendiente", title.trim(), new Date(dueIso));
        if (!granted) Alert.alert("Sin recordatorio", "La tarea se guardó, pero no se pudo programar la notificación.");
      } else await cancelReminder("task", saved.id);
      setNotice(editing ? "Tarea actualizada." : "Tarea creada.");
      setModal(false); await load();
    } catch (err) { setFormError(err instanceof Error ? err.message : "No se pudo guardar la tarea."); }
    finally { setSaving(false); }
  };

  const changeStatus = async (task: Task, status: TaskStatus) => {
    try { await taskService.setStatus(task.id, status); if (status === "Completada") await cancelReminder("task", task.id); setNotice(`Tarea cambiada a ${status.toLowerCase()}.`); await load(); }
    catch (err) { Alert.alert("No fue posible", err instanceof Error ? err.message : "Intenta de nuevo."); }
  };

  const remove = (task: Task) => Alert.alert("Eliminar tarea", `¿Seguro que quieres eliminar “${task.title}”?`, [
    { text: "Cancelar", style: "cancel" },
    { text: "Eliminar", style: "destructive", onPress: async () => {
      try { await taskService.remove(task.id); await cancelReminder("task", task.id); setNotice("Tarea eliminada."); await load(); }
      catch (err) { Alert.alert("No fue posible", err instanceof Error ? err.message : "Intenta de nuevo."); }
    } },
  ]);

  return (
    <Screen refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void load(true)} tintColor={colors.primary} />}>
      <PageHeader eyebrow="Organiza sin presión" title="Tareas" subtitle="Lo importante, ordenado y a tu ritmo." />
      <PrimaryButton label="＋ Nueva tarea" onPress={() => void openForm()} />
      {notice ? <Text style={sharedStyles.success}>{notice}</Text> : null}
      <Chips values={filters} selected={filter} onSelect={setFilter} />
      <LoadState loading={loading} error={error} empty={!loading && !error && tasks.length === 0 ? "Todo tranquilo por aquí, Carlitos. ✦" : undefined} onRetry={() => void load()} />
      {!loading && !error && tasks.map((task) => {
        const completed = task.status === "Completada";
        const overdue = Boolean(task.due_date && !completed && new Date(task.due_date).getTime() < Date.now());
        return (
          <Card key={task.id} style={[completed && styles.completed, overdue && styles.overdue]}>
            <View style={sharedStyles.between}>
              <Text style={[styles.taskTitle, completed && styles.strike]}>{task.title}</Text>
              <Text style={[styles.priority, task.priority === "Alta" && styles.high]}>{task.priority}</Text>
            </View>
            <Text style={[styles.status, task.status === "En progreso" && styles.inProgress]}>{task.status}</Text>
            {task.description ? <Text style={sharedStyles.body}>{task.description}</Text> : null}
            {task.due_date ? <Text style={[sharedStyles.muted, overdue && styles.overdueText]}>{overdue ? "Vencida · " : ""}{formatDateTime(task.due_date)}</Text> : <Text style={sharedStyles.muted}>Sin fecha límite</Text>}
            {reminderIds.has(task.id) ? <Text style={styles.reminderActive}>Recordatorio activo</Text> : null}
            <View style={sharedStyles.actions}>
              {completed ? <PrimaryButton label="Reabrir" onPress={() => void changeStatus(task, "Pendiente")} variant="soft" /> : <>
                <PrimaryButton label={task.status === "En progreso" ? "Pausar" : "Iniciar"} onPress={() => void changeStatus(task, task.status === "En progreso" ? "Pendiente" : "En progreso")} variant="soft" />
                <PrimaryButton label="Completar" onPress={() => void changeStatus(task, "Completada")} variant="soft" />
              </>}
              <PrimaryButton label="Editar" onPress={() => void openForm(task)} variant="soft" />
              <PrimaryButton label="Eliminar" onPress={() => remove(task)} variant="danger" />
            </View>
          </Card>
        );
      })}

      <FormModal visible={modal} title={editing ? "Editar tarea" : "Nueva tarea"} onClose={() => !saving && setModal(false)}>
        <Field label="Título *" value={title} onChangeText={setTitle} placeholder="Ej. Entregar proyecto" autoCapitalize="sentences" />
        <Field label="Descripción" value={description} onChangeText={setDescription} placeholder="Detalles opcionales" multiline />
        <Field label="Fecha y hora límite" value={due} onChangeText={setDue} placeholder="AAAA-MM-DDTHH:mm" autoCapitalize="none" />
        <Text style={styles.formLabel}>Prioridad</Text>
        <Chips values={priorities} selected={priority} onSelect={setPriority} />
        {due ? <View style={sharedStyles.between}><Text style={sharedStyles.body}>Programar recordatorio local</Text><Switch value={reminder} onValueChange={setReminder} trackColor={{ true: colors.primary }} /></View> : null}
        {formError ? <Text style={sharedStyles.error}>{formError}</Text> : null}
        <PrimaryButton label={saving ? "Guardando…" : "Guardar tarea"} onPress={() => void save()} disabled={saving} />
      </FormModal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  taskTitle: { flex: 1, color: colors.text, fontSize: 17, fontWeight: "900" },
  strike: { textDecorationLine: "line-through", color: colors.muted },
  completed: { opacity: 0.7 },
  overdue: { backgroundColor: colors.overdue, borderColor: "#F4B9C0" },
  overdueText: { color: colors.danger, fontWeight: "800" },
  priority: { color: colors.primaryDark, backgroundColor: colors.pinkSoft, borderRadius: 99, paddingHorizontal: 10, paddingVertical: 5, fontSize: 12, fontWeight: "800" },
  status: { alignSelf: "flex-start", color: colors.muted, backgroundColor: colors.cream, borderRadius: 99, paddingHorizontal: 10, paddingVertical: 5, fontSize: 12, fontWeight: "800" },
  inProgress: { color: colors.success, backgroundColor: colors.blue },
  reminderActive: { color: colors.success, fontSize: 12, fontWeight: "800" },
  high: { color: colors.danger, backgroundColor: "#FFE2E4" },
  formLabel: { color: colors.text, fontSize: 13, fontWeight: "700", marginBottom: -8 },
});
