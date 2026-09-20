/** Consulta el diagnostico y administra respaldos de la aplicacion. */

import { BackupDocument, BackupRestoreResult, SystemStatus } from "@/types";
import { request } from "./api";

export const systemService = {
  status: () => request<SystemStatus>("/system/status"),
  backup: () => request<BackupDocument>("/system/backup"),
  restore: (backup: BackupDocument, replaceExisting = true) =>
    request<BackupRestoreResult>("/system/backup/restore", {
      method: "POST",
      headers: { "X-Confirm-Restore": "restore" },
      body: JSON.stringify({ backup, replace_existing: replaceExisting }),
    }),
};
