import apiClient from "./client";

export async function getExamSessions() {
  const response = await apiClient.get("/exam-sessions");
  return response.data;
}

export async function getExamSession(id) {
  const response = await apiClient.get(`/exam-sessions/${id}`);
  return response.data;
}

export async function startExamSession(examId) {
  const response = await apiClient.post("/exam-sessions/start", {
    exam_id: examId,
  });
  return response.data;
}

export async function submitExamSession(sessionId) {
  const response = await apiClient.put(`/exam-sessions/submit/${sessionId}`);
  return response.data;
}
