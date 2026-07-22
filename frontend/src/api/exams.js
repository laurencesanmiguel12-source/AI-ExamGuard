import apiClient from "./client";

export async function getExams() {
  const response = await apiClient.get("/exams/");
  return response.data;
}

export async function getExam(id) {
  const response = await apiClient.get(`/exams/${id}`);
  return response.data;
}

export async function createExam(payload) {
  const response = await apiClient.post("/exams/", payload);
  return response.data;
}

export async function updateExam(id, payload) {
  const response = await apiClient.put(`/exams/${id}`, payload);
  return response.data;
}

export async function deleteExam(id) {
  await apiClient.delete(`/exams/${id}`);
}
