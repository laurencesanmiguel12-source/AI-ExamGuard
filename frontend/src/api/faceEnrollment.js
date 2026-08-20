import apiClient from "./client";

export async function enrollFace(studentId, blobs) {
  const form = new FormData();
  blobs.forEach((blob, i) => form.append("files", blob, `capture-${i}.jpg`));
  const response = await apiClient.post(`/students/${studentId}/face-enrollment`, form);
  return response.data;
}

export async function checkFace(sessionId, blob, question, clientConfidentCrop = false) {
  const form = new FormData();
  form.append("file", blob, "frame.jpg");
  if (question) {
    form.append("question_id", question.id);
    form.append("question_text", question.question_text);
    form.append("question_type", question.question_type);
  }
  if (clientConfidentCrop) {
    form.append("client_confident_crop", "true");
  }
  const response = await apiClient.post(`/exam-sessions/${sessionId}/face-check`, form);
  return response.data;
}
