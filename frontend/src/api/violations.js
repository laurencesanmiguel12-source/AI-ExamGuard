import apiClient from "./client";

export async function logViolation(sessionId, eventType) {
  const response = await apiClient.post(`/exam-sessions/${sessionId}/violations`, {
    event_type: eventType,
  });
  return response.data;
}

export async function getSessionRisk(sessionId) {
  const response = await apiClient.get(`/exam-sessions/${sessionId}/risk`);
  return response.data.risk_score;
}

export async function getLiveSessions() {
  const response = await apiClient.get("/exam-sessions/live");
  return response.data;
}
