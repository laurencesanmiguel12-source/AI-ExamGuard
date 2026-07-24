import apiClient from "./client";

export async function createExamChoice(examId, questionId, payload) {
  const response = await apiClient.post(`/exams/${examId}/questions/${questionId}/choices`, payload);
  return response.data;
}

export async function updateExamChoice(examId, questionId, choiceId, payload) {
  const response = await apiClient.put(
    `/exams/${examId}/questions/${questionId}/choices/${choiceId}`,
    payload
  );
  return response.data;
}

export async function deleteExamChoice(examId, questionId, choiceId) {
  await apiClient.delete(`/exams/${examId}/questions/${questionId}/choices/${choiceId}`);
}
