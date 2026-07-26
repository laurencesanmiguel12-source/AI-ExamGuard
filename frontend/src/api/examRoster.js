import apiClient from "./client";

export async function getExamRoster(examId) {
  const response = await apiClient.get(`/exams/${examId}/roster`);
  return response.data;
}

export async function getAvailableRosterStudents(examId) {
  const response = await apiClient.get(`/exams/${examId}/roster/available`);
  return response.data;
}

export async function addExamRosterStudent(examId, studentId) {
  const response = await apiClient.post(`/exams/${examId}/roster`, { student_id: studentId });
  return response.data;
}

export async function removeExamRosterStudent(examId, studentId) {
  await apiClient.delete(`/exams/${examId}/roster/${studentId}`);
}
