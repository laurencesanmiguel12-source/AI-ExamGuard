import apiClient from "./client";

export async function logViolation(sessionId, eventType, detail) {
  const response = await apiClient.post(`/exam-sessions/${sessionId}/violations`, {
    event_type: eventType,
    ...(detail ? { detail } : {}),
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
