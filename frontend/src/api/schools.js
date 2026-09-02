import apiClient from "./client";

export async function getSchools() {
  const response = await apiClient.get("/schools/");
  return response.data;
}

export async function registerSchool(payload) {
  const response = await apiClient.post("/schools/register", payload);
  return response.data;
}

// Dedicated endpoint rather than filtering getSchools(): that list only contains APPROVED
// schools (it feeds the student-registration picker), so a pending school would look like a 404
// to the very person who just registered it. This resolves any status and returns name/status
// only. Also avoids refetching every school on each login-page load.
export async function getSchoolBySlug(slug) {
  const response = await apiClient.get(`/schools/slug/${slug}`);
  return response.data;
}

export async function getSchoolsForReview(status) {
  const response = await apiClient.get("/schools/review", {
    params: status ? { status } : undefined,
  });
  return response.data;
}

export async function reviewSchool(schoolId, payload) {
  const response = await apiClient.put(`/schools/${schoolId}/review`, payload);
  return response.data;
}
