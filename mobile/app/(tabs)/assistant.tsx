/** Interfaz conversacional por texto y voz para el asistente multiagente. */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from "expo-audio";
import * as Speech from "expo-speech";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";

import { Card, PageHeader, Screen, sharedStyles } from "@/components/ui";
import { colors } from "@/constants/theme";
import { assistantService } from "@/services/assistant";
import { AssistantAgent, AssistantConversationMessage } from "@/types";

interface ChatMessage extends AssistantConversationMessage {
  id: number;
  agents?: AssistantAgent[];
  routingReason?: string;
}

type VoiceStage = "checking" | "idle" | "listening" | "transcribing" | "sending" | "speaking" | "unavailable";

const examples = [
  "¿Cuánto dinero me queda este mes?",
  "¿Qué tareas y eventos tengo pendientes?",
  "Prioriza mis correos no leídos y dime cuáles son urgentes.",
];

const agentLabel: Record<AssistantAgent, string> = {
  secretary: "Secretaría",
  financial: "Finanzas",
};

function voiceStatus(stage: VoiceStage, autoSend: boolean): { title: string; detail: string } {
  /** Traduce la maquina de estados de voz a mensajes visibles para el usuario. */

  if (stage === "checking") return { title: "Preparando control por voz…", detail: "Comprobando la grabadora compatible con Expo Go." };
  if (stage === "unavailable") return { title: "Voz no disponible", detail: "El chat escrito funciona; revisa el permiso del micrófono." };
  if (stage === "listening") return { title: "Te estoy escuchando…", detail: "Habla con naturalidad y toca el botón al terminar." };
  if (stage === "transcribing") return { title: "Transcribiendo localmente…", detail: "Whisper está convirtiendo el audio en texto en tu computador." };
  if (stage === "sending") return { title: "Kirby está pensando…", detail: "La transcripción ya llegó al orquestador multiagente." };
  if (stage === "speaking") return { title: "Kirby está respondiendo…", detail: "La respuesta también se está leyendo en voz alta." };
  return {
    title: "Control por voz listo",
    detail: autoSend
      ? "Toca el micrófono y vuelve a tocarlo al terminar; Kirby enviará la transcripción."
      : "Toca el micrófono, vuelve a tocarlo al terminar y revisa el texto antes de enviarlo.",
  };
}

export default function AssistantScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [voiceStage, setVoiceStage] = useState<VoiceStage>("checking");
  const [error, setError] = useState("");
  const [voiceAvailable, setVoiceAvailable] = useState<boolean | null>(null);
  const [speakReplies, setSpeakReplies] = useState(true);
  const [autoSendVoice, setAutoSendVoice] = useState(true);
  const [continuousConversation, setContinuousConversation] = useState(false);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const recorderState = useAudioRecorderState(recorder);
  const nextId = useRef(1);
  const messagesRef = useRef<ChatMessage[]>([]);
  const sendingRef = useRef(false);
  const speakRepliesRef = useRef(true);
  const autoSendVoiceRef = useRef(true);
  const continuousConversationRef = useRef(false);
  const voiceAvailableRef = useRef(false);
  const recordingRef = useRef(false);
  const sendMessageRef = useRef<(text?: string) => Promise<void>>(async () => undefined);
  const startListeningRef = useRef<() => Promise<void>>(async () => undefined);
  const stopListeningRef = useRef<() => Promise<void>>(async () => undefined);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recordingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const listening = recorderState.isRecording || voiceStage === "listening";

  useEffect(() => { speakRepliesRef.current = speakReplies; }, [speakReplies]);
  useEffect(() => { autoSendVoiceRef.current = autoSendVoice; }, [autoSendVoice]);
  useEffect(() => { continuousConversationRef.current = continuousConversation; }, [continuousConversation]);

  const finishVoiceReply = useCallback(() => {
    setVoiceStage("idle");
    if (!continuousConversationRef.current || !voiceAvailableRef.current) return;
    if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
    // En modo continuo, vuelve a escuchar despues de terminar la locucion.
    restartTimerRef.current = setTimeout(() => {
      void startListeningRef.current();
    }, 650);
  }, []);

  const sendMessage = useCallback(async (textOverride?: string) => {
    const text = (textOverride ?? draft).trim();
    if (!text || sendingRef.current) return;

    // Limita el historial para conservar contexto sin hacer crecer indefinidamente la solicitud.
    const history = messagesRef.current.slice(-20).map(({ role, content }) => ({ role, content }));
    const userMessage: ChatMessage = { id: nextId.current++, role: "user", content: text };
    const withUser = [...messagesRef.current, userMessage];
    messagesRef.current = withUser;
    setMessages(withUser);
    setDraft("");
    setError("");
    sendingRef.current = true;
    setSending(true);
    setVoiceStage("sending");

    try {
      const response = await assistantService.chat({ message: text, history });
      const assistantMessage: ChatMessage = {
        id: nextId.current++,
        role: "assistant",
        content: response.message,
        agents: response.agents,
        routingReason: response.routing_reason,
      };
      const withAssistant = [...messagesRef.current, assistantMessage];
      messagesRef.current = withAssistant;
      setMessages(withAssistant);
      if (speakRepliesRef.current) {
        await Speech.stop();
        setVoiceStage("speaking");
        Speech.speak(response.message, {
          language: "es-CO",
          rate: 0.95,
          onDone: finishVoiceReply,
          onStopped: () => setVoiceStage("idle"),
          onError: () => {
            setVoiceStage("idle");
            setError("La respuesta llegó, pero no fue posible reproducirla en voz alta.");
          },
        });
      } else {
        finishVoiceReply();
      }
    } catch (requestError) {
      setVoiceStage("idle");
      setError(requestError instanceof Error ? requestError.message : "No fue posible consultar el asistente.");
    } finally {
      sendingRef.current = false;
      setSending(false);
    }
  }, [draft, finishVoiceReply]);

  useEffect(() => { sendMessageRef.current = sendMessage; }, [sendMessage]);

  useEffect(() => {
    setVoiceAvailable(true);
    voiceAvailableRef.current = true;
    setVoiceStage("idle");
    return () => {
      if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
      if (recordingTimerRef.current) clearTimeout(recordingTimerRef.current);
      if (recordingRef.current) {
        recordingRef.current = false;
        void recorder.stop().catch(() => undefined);
      }
      void Speech.stop();
    };
  }, [recorder]);

  const stopListening = useCallback(async () => {
    if (!recordingRef.current) return;
    recordingRef.current = false;
    if (recordingTimerRef.current) {
      clearTimeout(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    setVoiceStage("transcribing");
    setError("");

    try {
      await recorder.stop();
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
      const audioUri = recorder.uri;
      if (!audioUri) throw new Error("La grabación no produjo un archivo de audio.");

      const transcription = await assistantService.transcribe(audioUri);
      const transcript = transcription.text.trim();
      if (!transcript) throw new Error("No se detectó una frase completa.");
      setDraft(transcript);
      // El usuario puede revisar la transcripcion o enviarla sin tocar la pantalla.
      if (autoSendVoiceRef.current) {
        await sendMessageRef.current(transcript);
      } else {
        setVoiceStage("idle");
      }
    } catch (transcriptionError) {
      setVoiceStage("idle");
      setError(
        transcriptionError instanceof Error
          ? transcriptionError.message
          : "No fue posible transcribir el audio.",
      );
    }
  }, [recorder]);

  const startListening = useCallback(async () => {
    if (sendingRef.current || recordingRef.current) return;
    setError("");
    await Speech.stop();
    try {
      const permission = await AudioModule.requestRecordingPermissionsAsync();
      if (!permission.granted) {
        setVoiceStage("idle");
        setError("Debes permitir el micrófono para grabar tu solicitud.");
        return;
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await recorder.prepareToRecordAsync();
      recorder.record();
      recordingRef.current = true;
      setVoiceStage("listening");
      // Cierra automaticamente grabaciones olvidadas y limita el tamaño de carga.
      recordingTimerRef.current = setTimeout(() => {
        void stopListeningRef.current();
      }, 30000);
    } catch {
      recordingRef.current = false;
      setVoiceStage("idle");
      setError("No fue posible iniciar la grabación de voz.");
    }
  }, [recorder]);

  useEffect(() => { startListeningRef.current = startListening; }, [startListening]);
  useEffect(() => { stopListeningRef.current = stopListening; }, [stopListening]);

  const toggleListening = async () => {
    if (listening) {
      await stopListening();
      return;
    }
    await startListening();
  };

  const repeatLastAnswer = async () => {
    const lastAnswer = [...messages].reverse().find((message) => message.role === "assistant");
    if (!lastAnswer) return;
    await Speech.stop();
    setVoiceStage("speaking");
    Speech.speak(lastAnswer.content, {
      language: "es-CO",
      rate: 0.95,
      onDone: finishVoiceReply,
      onStopped: () => setVoiceStage("idle"),
      onError: () => {
        setVoiceStage("idle");
        setError("No fue posible reproducir la respuesta en voz alta.");
      },
    });
  };

  const clearConversation = () => {
    if (sendingRef.current) return;
    if (recordingRef.current) {
      recordingRef.current = false;
      void recorder.stop().catch(() => undefined);
    }
    if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
    if (recordingTimerRef.current) clearTimeout(recordingTimerRef.current);
    void Speech.stop();
    messagesRef.current = [];
    setMessages([]);
    setDraft("");
    setError("");
    setVoiceStage(voiceAvailable ? "idle" : "unavailable");
  };

  const currentVoiceStatus = voiceStatus(voiceStage, autoSendVoice);

  const toggleContinuousConversation = (enabled: boolean) => {
    setContinuousConversation(enabled);
    if (enabled) {
      setAutoSendVoice(true);
      setSpeakReplies(true);
    } else if (restartTimerRef.current) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }
  };

  return (
    <Screen>
      <PageHeader
        eyebrow="IA multiagente"
        title="Habla con Kirby"
        subtitle="Pregunta por tus tareas, agenda, correo, gastos o presupuesto."
      />

      <Card style={styles.voiceCard}>
        <View style={sharedStyles.between}>
          <View style={styles.voiceCopy}>
            <Text accessibilityLiveRegion="polite" style={styles.voiceTitle}>{currentVoiceStatus.title}</Text>
            <Text style={sharedStyles.muted}>{currentVoiceStatus.detail}</Text>
          </View>
          <Pressable
            accessibilityLabel={listening ? "Detener dictado" : "Iniciar dictado"}
            accessibilityRole="button"
            disabled={sending || voiceAvailable !== true || voiceStage === "checking"}
            onPress={() => void toggleListening()}
            style={({ pressed }) => [
              styles.micButton,
              listening && styles.micButtonActive,
              (pressed || sending || voiceAvailable !== true) && styles.pressed,
            ]}
          >
            {voiceStage === "checking" || voiceStage === "transcribing" || voiceStage === "sending" ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.micIcon}>{listening ? "■" : "●"}</Text>
            )}
          </Pressable>
        </View>
        <View style={styles.switches}>
          <View style={sharedStyles.between}>
            <Text style={styles.switchLabel}>Enviar al terminar de hablar</Text>
            <Switch
              value={autoSendVoice}
              onValueChange={setAutoSendVoice}
              trackColor={{ false: colors.border, true: colors.primary }}
            />
          </View>
          <View style={sharedStyles.between}>
            <Text style={styles.switchLabel}>Leer respuestas en voz alta</Text>
            <Switch
              value={speakReplies}
              onValueChange={setSpeakReplies}
              trackColor={{ false: colors.border, true: colors.primary }}
            />
          </View>
          <View style={sharedStyles.between}>
            <View style={styles.switchCopy}>
              <Text style={styles.switchLabel}>Conversación continua</Text>
              <Text style={sharedStyles.muted}>Reabre el micrófono después de cada respuesta.</Text>
            </View>
            <Switch
              value={continuousConversation}
              onValueChange={toggleContinuousConversation}
              trackColor={{ false: colors.border, true: colors.primary }}
            />
          </View>
        </View>
      </Card>

      {messages.length === 0 ? (
        <Card>
          <Text style={sharedStyles.sectionTitle}>Puedes probar</Text>
          {examples.map((example) => (
            <Pressable key={example} onPress={() => setDraft(example)} style={styles.example}>
              <Text style={styles.exampleText}>{example}</Text>
            </Pressable>
          ))}
        </Card>
      ) : (
        <View style={styles.conversation}>
          {messages.map((message) => (
            <View
              key={message.id}
              style={[
                styles.bubble,
                message.role === "user" ? styles.userBubble : styles.assistantBubble,
              ]}
            >
              <Text style={styles.bubbleAuthor}>{message.role === "user" ? "Tú" : "Kirby"}</Text>
              <Text selectable style={styles.bubbleText}>{message.content}</Text>
              {message.agents ? (
                <Text style={styles.agentText}>
                  Agentes: {message.agents.map((agent) => agentLabel[agent]).join(" + ")}
                </Text>
              ) : null}
              {message.routingReason ? (
                <Text style={styles.reason}>Ruta: {message.routingReason}</Text>
              ) : null}
            </View>
          ))}
        </View>
      )}

      {sending ? (
        <View style={styles.loadingRow}>
          <ActivityIndicator color={colors.primary} />
          <Text style={sharedStyles.muted}>Kirby está consultando a los agentes…</Text>
        </View>
      ) : null}
      {error ? <Text style={sharedStyles.error}>{error}</Text> : null}

      <Card>
        <TextInput
          accessibilityLabel="Mensaje para Kirby"
          editable={!sending}
          multiline
          onChangeText={setDraft}
          onSubmitEditing={() => void sendMessage()}
          placeholder="Escribe o dicta una solicitud…"
          placeholderTextColor="#A997A7"
          returnKeyType="send"
          style={styles.input}
          value={draft}
        />
        <View style={styles.actions}>
          <Pressable
            accessibilityRole="button"
            disabled={!draft.trim() || sending}
            onPress={() => void sendMessage()}
            style={({ pressed }) => [styles.sendButton, (pressed || !draft.trim() || sending) && styles.pressed]}
          >
            <Text style={styles.sendText}>Enviar</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={() => void repeatLastAnswer()} style={styles.softButton}>
            <Text style={styles.softButtonText}>Repetir voz</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={clearConversation} style={styles.softButton}>
            <Text style={styles.softButtonText}>Limpiar</Text>
          </Pressable>
        </View>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  voiceCard: { backgroundColor: colors.blue },
  voiceCopy: { flex: 1, paddingRight: 10 },
  voiceTitle: { color: colors.text, fontSize: 17, fontWeight: "900", marginBottom: 4 },
  switches: { gap: 8 },
  switchLabel: { color: colors.text, fontSize: 14, fontWeight: "700", flex: 1 },
  switchCopy: { flex: 1 },
  micButton: {
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  micButtonActive: { backgroundColor: colors.danger },
  micIcon: { color: "white", fontSize: 21, fontWeight: "900" },
  pressed: { opacity: 0.5 },
  example: { backgroundColor: colors.background, borderRadius: 14, padding: 13 },
  exampleText: { color: colors.primaryDark, fontSize: 14, lineHeight: 20, fontWeight: "700" },
  conversation: { gap: 10 },
  bubble: { maxWidth: "92%", padding: 14, borderRadius: 18, gap: 5 },
  userBubble: { alignSelf: "flex-end", backgroundColor: colors.pinkSoft, borderBottomRightRadius: 5 },
  assistantBubble: { alignSelf: "flex-start", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderBottomLeftRadius: 5 },
  bubbleAuthor: { color: colors.primaryDark, fontSize: 12, fontWeight: "900", textTransform: "uppercase" },
  bubbleText: { color: colors.text, fontSize: 15, lineHeight: 21 },
  agentText: { color: colors.success, fontSize: 12, fontWeight: "800", marginTop: 3 },
  reason: { color: colors.muted, fontSize: 11, lineHeight: 16 },
  loadingRow: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 9 },
  input: { minHeight: 92, color: colors.text, fontSize: 15, lineHeight: 21, textAlignVertical: "top" },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  sendButton: { backgroundColor: colors.primary, borderRadius: 14, minHeight: 44, paddingHorizontal: 20, alignItems: "center", justifyContent: "center" },
  sendText: { color: "white", fontWeight: "900" },
  softButton: { backgroundColor: colors.pinkSoft, borderRadius: 14, minHeight: 44, paddingHorizontal: 14, alignItems: "center", justifyContent: "center" },
  softButtonText: { color: colors.primaryDark, fontWeight: "800" },
});
