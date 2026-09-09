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

export async function bulkAddExamRosterStudents(examId) {
  const response = await apiClient.post(`/exams/${examId}/roster/bulk-add`);
  return response.data;
}

export async function removeExamRosterStudent(examId, studentId) {
  await apiClient.delete(`/exams/${examId}/roster/${studentId}`);
}

// Which of the two roster sources is actually in force, and whether it admits anybody. The two
// situations this tells apart look identical on screen otherwise: an exam inheriting a healthy
// class list, and one pointing at a section with nobody enrolled.
export async function getExamRosterSource(examId) {
  const response = await apiClient.get(`/exams/${examId}/roster/source`);
  return response.data;
}
