import apiClient from "./client";

export async function getStudents() {
  const response = await apiClient.get("/students/");
  return response.data;
}

export async function createStudent(payload) {
  const response = await apiClient.post("/students/", payload);
  return response.data;
}

export async function updateStudent(id, payload) {
  const response = await apiClient.put(`/students/${id}`, payload);
  return response.data;
}

export async function deleteStudent(id) {
  await apiClient.delete(`/students/${id}`);
}
