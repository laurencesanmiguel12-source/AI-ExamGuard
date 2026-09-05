import apiClient from "./client";

export async function getPendingTrainingCandidates() {
  const response = await apiClient.get("/admin/training-review/pending");
  return response.data;
}

export async function reviewTrainingCandidate(violationId, decision) {
  const response = await apiClient.put(`/admin/training-review/${violationId}`, { decision });
  return response.data;
}

// Near misses: frames the detector scored as plausible but did not act on. A separate queue
// because they are not violations - nothing happened to the student - and because these are the
// detector's failures, which is exactly what makes them worth training on.
export async function getPendingNearMisses() {
  const response = await apiClient.get("/admin/near-miss-review/pending");
  return response.data;
}

export async function reviewNearMiss(captureId, decision) {
  const response = await apiClient.put(`/admin/near-miss-review/${captureId}`, { decision });
  return response.data;
}

export async function getNearMissEvidenceBlobUrl(captureId) {
  const response = await apiClient.get(`/admin/near-miss-review/${captureId}/evidence`, {
    responseType: "blob",
  });
  return URL.createObjectURL(response.data);
}
