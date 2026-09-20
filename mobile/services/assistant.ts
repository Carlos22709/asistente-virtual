/** Operaciones remotas de chat y carga de audio del asistente. */

import { File } from "expo-file-system";

import { request } from "@/services/api";
import {
  AssistantChatRequest,
  AssistantChatResponse,
  AssistantTranscriptionResponse,
} from "@/types";

export const assistantService = {
  chat: (payload: AssistantChatRequest) =>
    request<AssistantChatResponse>("/assistant/chat", {
      method: "POST",
      body: JSON.stringify(payload),
      timeoutMs: 120000,
    }),
  transcribe: (uri: string) => {
    const audioFile = new File(uri);
    if (!audioFile.exists || audioFile.size === 0) {
      throw new Error("La grabación no produjo un archivo de audio legible.");
    }

    const extension = audioFile.extension || ".m4a";
    const formData = new FormData();
    formData.append("audio", audioFile, "kirby-voice" + extension);
    return request<AssistantTranscriptionResponse>("/assistant/transcribe", {
      method: "POST",
      body: formData,
      timeoutMs: 120000,
    });
  },
};
