import apiClient from "./client";

export async function getExamQuestions(examId) {
  const response = await apiClient.get(`/exams/${examId}/questions`);
  return response.data;
}

export async function createExamQuestion(examId, payload) {
  const response = await apiClient.post(`/exams/${examId}/questions`, payload);
  return response.data;
}

export async function updateExamQuestion(examId, questionId, payload) {
  const response = await apiClient.put(`/exams/${examId}/questions/${questionId}`, payload);
  return response.data;
}

export async function deleteExamQuestion(examId, questionId) {
  await apiClient.delete(`/exams/${examId}/questions/${questionId}`);
}

export async function importExamQuestionsCsv(examId, file) {
  const form = new FormData();
  form.append("file", file);
  const response = await apiClient.post(`/exams/${examId}/questions/import`, form);
  return response.data;
}
