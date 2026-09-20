/** Persiste de forma segura la URL y el token usados para conectar la API. */

import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const API_URL_KEY = "kirby:configuration:api-url";
const API_TOKEN_KEY = "kirby:configuration:api-token";
const DEFAULT_API_URL = (
  process.env.EXPO_PUBLIC_API_URL ?? "http://127.0.0.1:3000"
).replace(/\/$/, "");

export interface ApiConfiguration {
  apiUrl: string;
  apiToken: string;
}

let cachedConfiguration: ApiConfiguration | null = null;

async function readToken(): Promise<string> {
  if (Platform.OS === "web") return (await AsyncStorage.getItem(API_TOKEN_KEY)) ?? "";
  try {
    return (await SecureStore.getItemAsync(API_TOKEN_KEY)) ?? "";
  } catch {
    return "";
  }
}

async function writeToken(token: string): Promise<void> {
  if (Platform.OS === "web") {
    if (token) await AsyncStorage.setItem(API_TOKEN_KEY, token);
    else await AsyncStorage.removeItem(API_TOKEN_KEY);
    return;
  }
  if (token) await SecureStore.setItemAsync(API_TOKEN_KEY, token);
  else await SecureStore.deleteItemAsync(API_TOKEN_KEY);
}

export function normalizeApiUrl(value: string): string {
  const normalized = value.trim().replace(/\/$/, "");
  const parsed = new URL(normalized);
  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("La URL debe comenzar por http:// o https://");
  }
  return normalized;
}

function resolveStoredApiUrl(storedUrl: string | null): string {
  // Al activar Tailscale, reemplaza automaticamente una IP local antigua.
  if (!storedUrl) return DEFAULT_API_URL;
  let normalizedStoredUrl: string;
  try {
    normalizedStoredUrl = normalizeApiUrl(storedUrl);
  } catch {
    return DEFAULT_API_URL;
  }

  const runtime = new URL(DEFAULT_API_URL);
  const stored = new URL(normalizedStoredUrl);
  const runtimeUsesTailscale = /^100\./.test(runtime.hostname);
  const storedUsesPreviousLocalNetwork =
    stored.protocol === "http:" &&
    (
      stored.hostname === "127.0.0.1" ||
      stored.hostname === "localhost" ||
      /^10\./.test(stored.hostname) ||
      /^192\.168\./.test(stored.hostname) ||
      /^172\.(1[6-9]|2\d|3[01])\./.test(stored.hostname)
    );

  if (
    runtimeUsesTailscale &&
    storedUsesPreviousLocalNetwork &&
    stored.hostname !== runtime.hostname
  ) {
    return DEFAULT_API_URL;
  }
  return normalizedStoredUrl;
}

export async function getApiConfiguration(): Promise<ApiConfiguration> {
  /** Recupera una configuracion cacheada sin exponer el token en variables publicas. */

  if (cachedConfiguration) return cachedConfiguration;
  const [storedUrl, apiToken] = await Promise.all([
    AsyncStorage.getItem(API_URL_KEY),
    readToken(),
  ]);
  const apiUrl = resolveStoredApiUrl(storedUrl);
  if (storedUrl && apiUrl === DEFAULT_API_URL && storedUrl.trim().replace(/\/$/, "") !== apiUrl) {
    await AsyncStorage.setItem(API_URL_KEY, apiUrl);
  }
  cachedConfiguration = { apiUrl, apiToken };
  return cachedConfiguration;
}

export async function saveApiConfiguration(
  configuration: ApiConfiguration,
): Promise<ApiConfiguration> {
  /** Valida la URL y guarda el token en SecureStore cuando la plataforma lo permite. */

  const normalized: ApiConfiguration = {
    apiUrl: normalizeApiUrl(configuration.apiUrl),
    apiToken: configuration.apiToken.trim(),
  };
  await Promise.all([
    AsyncStorage.setItem(API_URL_KEY, normalized.apiUrl),
    writeToken(normalized.apiToken),
  ]);
  cachedConfiguration = normalized;
  return normalized;
}

export function defaultApiUrl(): string {
  return DEFAULT_API_URL;
}
