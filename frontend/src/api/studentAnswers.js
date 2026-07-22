import apiClient from "./client";

export async function saveAnswer(sessionId, questionId, choiceId) {
  const response = await apiClient.post(`/exam-sessions/${sessionId}/answers`, {
    question_id: questionId,
    choice_id: choiceId,
  });
  return response.data;
}

export async function getAnswers(sessionId) {
  const response = await apiClient.get(`/exam-sessions/${sessionId}/answers`);
  return response.data;
}
