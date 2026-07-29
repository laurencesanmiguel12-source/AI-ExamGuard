import apiClient from "./client";

export async function previewPurge() {
  const response = await apiClient.get("/admin/retention/preview");
  return response.data;
}

export async function purgeExpiredEvidence() {
  const response = await apiClient.post("/admin/retention/purge");
  return response.data;
}
