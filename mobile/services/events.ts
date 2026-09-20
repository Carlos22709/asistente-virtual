/** Cliente CRUD para eventos de agenda. */

import { EventInput, EventItem } from "@/types";
import { queryString, request } from "./api";

export const eventService = {
  list: (filters: { date_from?: string; date_to?: string; upcoming?: boolean } = {}) =>
    request<EventItem[]>(`/events${queryString(filters)}`),
  create: (input: EventInput) =>
    request<EventItem>("/events", { method: "POST", body: JSON.stringify(input) }),
  update: (id: number, input: EventInput) =>
    request<EventItem>(`/events/${id}`, { method: "PUT", body: JSON.stringify(input) }),
  remove: (id: number) => request<void>(`/events/${id}`, { method: "DELETE" }),
};
