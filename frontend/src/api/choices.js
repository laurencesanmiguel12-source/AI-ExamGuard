import apiClient from "./client";

export async function getChoices() {
  const response = await apiClient.get("/choices");
  return response.data;
}

export async function createChoice(payload) {
  const response = await apiClient.post("/choices", payload);
  return response.data;
}

export async function updateChoice(id, payload) {
  const response = await apiClient.put(`/choices/${id}`, payload);
  return response.data;
}

export async function deleteChoice(id) {
  await apiClient.delete(`/choices/${id}`);
}
