import apiClient from "./client";

export async function getInstructorSubjects(instructorId) {
  const response = await apiClient.get(`/instructors/${instructorId}/subjects/`);
  return response.data;
}

export async function assignInstructorSubject(instructorId, subjectId) {
  const response = await apiClient.post(`/instructors/${instructorId}/subjects/`, { subject_id: subjectId });
  return response.data;
}

export async function unassignInstructorSubject(instructorId, subjectId) {
  await apiClient.delete(`/instructors/${instructorId}/subjects/${subjectId}`);
}
