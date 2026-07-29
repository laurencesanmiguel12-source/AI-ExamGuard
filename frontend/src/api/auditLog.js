import apiClient from "./client";

export async function getAuditLog() {
  const response = await apiClient.get("/admin/audit-log");
  return response.data;
}
