import apiClient from "./client";

function upload(path, file) {
  const form = new FormData();
  form.append("file", file);
  return apiClient.post(path, form).then((r) => r.data);
}

export async function importSetupCsv(file) {
  return upload("/admin/setup-import", file);
}

// The same import, run and thrown away. The counts come back meaning "would create", and the
// response carries preview: true so the UI never reads like a receipt for something that has not
// happened.
export async function previewSetupCsv(file) {
  return upload("/admin/setup-import/preview", file);
}

export async function getSetupReadiness() {
  const response = await apiClient.get("/admin/setup-import/readiness");
  return response.data;
}
