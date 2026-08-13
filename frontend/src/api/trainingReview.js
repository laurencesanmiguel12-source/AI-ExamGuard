import apiClient from "./client";

export async function getPendingTrainingCandidates() {
  const response = await apiClient.get("/admin/training-review/pending");
  return response.data;
}

export async function reviewTrainingCandidate(violationId, decision) {
  const response = await apiClient.put(`/admin/training-review/${violationId}`, { decision });
  return response.data;
}
