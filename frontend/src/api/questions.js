import apiClient from "./client";

export async function getQuestions() {
  const response = await apiClient.get("/questions");
  return response.data;
}

export async function createQuestion(payload) {
  const response = await apiClient.post("/questions", payload);
  return response.data;
}

export async function updateQuestion(id, payload) {
  const response = await apiClient.put(`/questions/${id}`, payload);
  return response.data;
}

export async function deleteQuestion(id) {
  await apiClient.delete(`/questions/${id}`);
}
