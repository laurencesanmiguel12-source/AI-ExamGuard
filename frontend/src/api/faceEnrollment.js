import apiClient from "./client";

export async function enrollFace(studentId, blobs) {
  const form = new FormData();
  blobs.forEach((blob, i) => form.append("files", blob, `capture-${i}.jpg`));
  const response = await apiClient.post(`/students/${studentId}/face-enrollment`, form);
  return response.data;
}

export async function checkFace(sessionId, blob) {
  const form = new FormData();
  form.append("file", blob, "frame.jpg");
  const response = await apiClient.post(`/exam-sessions/${sessionId}/face-check`, form);
  return response.data;
}
