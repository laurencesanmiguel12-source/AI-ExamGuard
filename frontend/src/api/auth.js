import apiClient from "./client";

export async function login(email, password) {
  const response = await apiClient.post("/auth/login", { email, password });
  return response.data;
}

export async function register(payload) {
  const response = await apiClient.post("/auth/register", payload);
  return response.data;
}

export async function getMe() {
  const response = await apiClient.get("/auth/me");
  return response.data;
}
