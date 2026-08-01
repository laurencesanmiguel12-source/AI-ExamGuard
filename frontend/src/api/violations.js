import apiClient from "./client";

export async function logViolation(sessionId, eventType, detail, evidenceBlob) {
  const form = new FormData();
  form.append("event_type", eventType);
  if (detail) form.append("detail", detail);
  if (evidenceBlob) form.append("evidence", evidenceBlob, "evidence.jpg");
  const response = await apiClient.post(`/exam-sessions/${sessionId}/violations`, form);
  return response.data;
}

export async function getSessionRisk(sessionId) {
  const response = await apiClient.get(`/exam-sessions/${sessionId}/risk`);
  return response.data.risk_score;
}

export async function getSessionRiskSummary(sessionId) {
  const response = await apiClient.get(`/exam-sessions/${sessionId}/risk-summary`);
  return response.data;
}

export async function getSessionViolations(sessionId) {
  const response = await apiClient.get(`/exam-sessions/${sessionId}/violations`);
  return response.data;
}

export async function getLiveSessions() {
  const response = await apiClient.get("/exam-sessions/live");
  return response.data;
}

export async function fileAppeal(violationId, reason) {
  const response = await apiClient.post(`/violations/${violationId}/appeal`, { reason });
  return response.data;
}

export async function reviewAppeal(violationId, status, response) {
  const res = await apiClient.put(`/violations/${violationId}/appeal-review`, { status, response });
  return res.data;
}

export async function getEvidenceBlobUrl(violationId) {
  const response = await apiClient.get(`/violations/${violationId}/evidence`, { responseType: "blob" });
  return URL.createObjectURL(response.data);
}
