import apiClient from "./client";

export async function getSubjects() {
  const response = await apiClient.get("/subjects/");
  return response.data;
}

export async function createSubject(payload) {
  const response = await apiClient.post("/subjects/", payload);
  return response.data;
}

export async function updateSubject(id, payload) {
  const response = await apiClient.put(`/subjects/${id}`, payload);
  return response.data;
}

export async function deleteSubject(id) {
  await apiClient.delete(`/subjects/${id}`);
}
