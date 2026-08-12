import apiClient from "./client";

export async function getInstructorAnalytics() {
  const response = await apiClient.get("/analytics/instructor");
  return response.data;
}

export async function getSchoolAnalytics() {
  const response = await apiClient.get("/analytics/school");
  return response.data;
}
