import apiClient from "./client";

// The academic hierarchy: year → term → section → enrolment. Everything here is school-scoped by
// the server from the caller's own token; no school id is ever sent, because a school id in a
// payload is an invitation to write into somebody else's school.

export async function getAcademicYears() {
  const response = await apiClient.get("/academic/years");
  return response.data;
}

export async function getCurrentAcademicYear() {
  const response = await apiClient.get("/academic/years/current");
  return response.data;
}

export async function createAcademicYear(payload) {
  const response = await apiClient.post("/academic/years", payload);
  return response.data;
}

export async function setCurrentAcademicYear(yearId) {
  const response = await apiClient.put(`/academic/years/${yearId}/current`);
  return response.data;
}

export async function updateAcademicYear(yearId, payload) {
  const response = await apiClient.put(`/academic/years/${yearId}`, payload);
  return response.data;
}

export async function deleteAcademicYear(yearId) {
  await apiClient.delete(`/academic/years/${yearId}`);
}

export async function getTerms(academicYearId) {
  const response = await apiClient.get("/academic/terms", {
    params: academicYearId ? { academic_year_id: academicYearId } : undefined,
  });
  return response.data;
}

export async function getCurrentTerm() {
  const response = await apiClient.get("/academic/terms/current");
  return response.data;
}

export async function createTerm(payload) {
  const response = await apiClient.post("/academic/terms", payload);
  return response.data;
}

export async function setTermStatus(termId, status) {
  const response = await apiClient.put(`/academic/terms/${termId}/status`, { status });
  return response.data;
}

export async function updateTerm(termId, payload) {
  const response = await apiClient.put(`/academic/terms/${termId}`, payload);
  return response.data;
}

export async function deleteTerm(termId) {
  await apiClient.delete(`/academic/terms/${termId}`);
}

export async function getSections({ termId, instructorId } = {}) {
  const params = {};
  if (termId) params.term_id = termId;
  if (instructorId) params.instructor_id = instructorId;
  const response = await apiClient.get("/academic/sections", { params });
  return response.data;
}

export async function getSection(sectionId) {
  const response = await apiClient.get(`/academic/sections/${sectionId}`);
  return response.data;
}

export async function createSection(payload) {
  const response = await apiClient.post("/academic/sections", payload);
  return response.data;
}

export async function updateSection(sectionId, payload) {
  const response = await apiClient.put(`/academic/sections/${sectionId}`, payload);
  return response.data;
}

export async function deleteSection(sectionId) {
  await apiClient.delete(`/academic/sections/${sectionId}`);
}

// active_only=false so the class list can show DROPPED and COMPLETED rows too - a roster that
// silently hides a dropped student looks like the student was never enrolled at all.
export async function getSectionRoster(sectionId, { activeOnly = true } = {}) {
  const response = await apiClient.get(`/academic/sections/${sectionId}/roster`, {
    params: { active_only: activeOnly },
  });
  return response.data;
}

export async function enrollStudents(sectionId, studentIds) {
  const response = await apiClient.post(`/academic/sections/${sectionId}/enroll`, {
    student_ids: studentIds,
  });
  return response.data;
}

export async function setEnrollmentStatus(sectionId, studentId, status) {
  const response = await apiClient.put(
    `/academic/sections/${sectionId}/enrollment/${studentId}`,
    { status }
  );
  return response.data;
}
