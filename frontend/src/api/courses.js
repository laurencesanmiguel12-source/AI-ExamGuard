import apiClient from "./client";

export async function getCourses(schoolId) {
  const response = await apiClient.get("/courses/", { params: { school_id: schoolId } });
  return response.data;
}

export async function createCourse(payload) {
  const response = await apiClient.post("/courses/", payload);
  return response.data;
}

export async function updateCourse(id, payload) {
  const response = await apiClient.put(`/courses/${id}`, payload);
  return response.data;
}

export async function deleteCourse(id) {
  await apiClient.delete(`/courses/${id}`);
}
