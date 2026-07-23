import apiClient from "./client";

export async function getExamReport(examId) {
  const response = await apiClient.get(`/exams/${examId}/report`);
  return response.data;
}
