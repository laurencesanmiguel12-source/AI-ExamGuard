import apiClient from "./client";

export async function checkObjects(sessionId, blob) {
  const form = new FormData();
  form.append("file", blob, "frame.jpg");
  const response = await apiClient.post(`/exam-sessions/${sessionId}/object-check`, form);
  return response.data;
}
