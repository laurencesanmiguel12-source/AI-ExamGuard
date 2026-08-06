import apiClient from "./client";

export async function getSchools() {
  const response = await apiClient.get("/schools/");
  return response.data;
}

export async function registerSchool(payload) {
  const response = await apiClient.post("/schools/register", payload);
  return response.data;
}
