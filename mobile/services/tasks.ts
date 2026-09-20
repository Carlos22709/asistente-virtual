/** Cliente CRUD, filtros y cambios de estado para tareas. */

import { request, queryString } from "./api";
import { Task, TaskInput, TaskPriority, TaskStatus } from "@/types";

export const taskService = {
  list: (filters: { completed?: boolean; priority?: TaskPriority; task_status?: TaskStatus } = {}) =>
    request<Task[]>(`/tasks${queryString(filters)}`),
  create: (input: TaskInput) => request<Task>("/tasks", { method: "POST", body: JSON.stringify(input) }),
  update: (id: number, input: TaskInput) =>
    request<Task>(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(input) }),
  complete: (id: number, completed: boolean) =>
    request<Task>(`/tasks/${id}/complete`, { method: "PATCH", body: JSON.stringify({ completed }) }),
  setStatus: (id: number, status: TaskStatus) =>
    request<Task>(`/tasks/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
  remove: (id: number) => request<void>(`/tasks/${id}`, { method: "DELETE" }),
};
