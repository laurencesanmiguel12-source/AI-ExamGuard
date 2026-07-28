import apiClient from "./client";

export async function getSystemStatus() {
  const response = await apiClient.get("/admin/system-status");
  return response.data;
}
