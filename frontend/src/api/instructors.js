import apiClient from "./client";

export async function getInstructors() {
  const response = await apiClient.get("/instructors/");
  return response.data;
}

export async function createInstructor(payload) {
  const response = await apiClient.post("/instructors/", payload);
  return response.data;
}

export async function updateInstructor(id, payload) {
  const response = await apiClient.put(`/instructors/${id}`, payload);
  return response.data;
}

export async function deleteInstructor(id) {
  await apiClient.delete(`/instructors/${id}`);
}
