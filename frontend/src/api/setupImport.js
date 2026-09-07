import apiClient from "./client";

export async function importSetupCsv(file) {
  const form = new FormData();
  form.append("file", file);
  const response = await apiClient.post("/admin/setup-import", form);
  return response.data;
}
