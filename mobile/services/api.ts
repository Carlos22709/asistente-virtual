/** Cliente HTTP comun con autenticacion, timeout y errores normalizados. */

import { fetch as expoFetch } from "expo/fetch";

import { getApiConfiguration } from "./configuration";

export interface ApiRequestOptions extends RequestInit {
  timeoutMs?: number;
}

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function fetchAttempt(
  url: string,
  token: string,
  options?: ApiRequestOptions,
): Promise<Response> {
  // AbortController evita que una red movil inestable deje la interfaz bloqueada.
  const { timeoutMs = 12000, ...fetchOptions } = options ?? {};
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const headers = new Headers(fetchOptions.headers);
  const isFormData = typeof FormData !== "undefined" && fetchOptions.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token && !headers.has("Authorization")) headers.set("Authorization", "Bearer " + token);
  try {
    return await expoFetch(url, {
      ...fetchOptions,
      signal: controller.signal,
      headers,
    });
  } finally {
    clearTimeout(timeout);
  }
}

export async function request<T>(path: string, options?: ApiRequestOptions): Promise<T> {
  /** Ejecuta una peticion autenticada y traduce fallos tecnicos a mensajes legibles. */

  const configuration = await getApiConfiguration();
  const method = (options?.method ?? "GET").toUpperCase();
  // Solo se reintentan lecturas idempotentes; repetir una escritura podria duplicarla.
  const attempts = method === "GET" ? 2 : 1;
  let response: Response | null = null;

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      response = await fetchAttempt(
        configuration.apiUrl + path,
        configuration.apiToken,
        options,
      );
      if (![502, 503, 504].includes(response.status) || attempt === attempts - 1) break;
    } catch (error) {
      if (attempt < attempts - 1) continue;
      if (error instanceof Error && error.name === "AbortError") {
        throw new ApiError(
          "El servidor tardó demasiado en responder. Revisa la red y vuelve a intentar.",
          0,
        );
      }
      const detail = error instanceof Error && error.message
        ? " Detalle: " + error.message
        : "";
      throw new ApiError(
        "No se pudo conectar con " + configuration.apiUrl + path + "." + detail,
        0,
      );
    }
  }

  if (!response) throw new ApiError("No se pudo conectar con el servidor.", 0);
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(". ")
      : data.detail;
    throw new ApiError(detail || "No se pudo completar la operación.", response.status);
  }
  return data as T;
}

export function queryString(values: Record<string, string | number | boolean | undefined>): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const query = params.toString();
  return query ? "?" + query : "";
}
