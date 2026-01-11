/**
 * # Papers API Functions
 * 
 * API functions for paper-related operations.
 */
import { apiClient } from "./client";
import type { Paper, PaperListResponse } from "@/types/paper";

const API_BASE = "/api/v1/papers";

export async function uploadPaper(file: File): Promise<Paper> {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await apiClient.post<Paper>(API_BASE, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  
  return response.data;
}

export async function getPapers(limit = 100, offset = 0): Promise<PaperListResponse> {
  const response = await apiClient.get<PaperListResponse>(API_BASE, {
    params: { limit, offset },
  });
  
  return response.data;
}

export async function getPaper(id: string): Promise<Paper> {
  const response = await apiClient.get<Paper>(`${API_BASE}/${id}`);
  return response.data;
}

export async function deletePaper(id: string): Promise<void> {
  await apiClient.delete(`${API_BASE}/${id}`);
}

export async function importFromDOI(doi: string): Promise<Paper> {
  const response = await apiClient.post<Paper>(`${API_BASE}/import-doi`, {
    doi,
  });
  return response.data;
}

export async function getPaperChunks(paperId: string) {
  const response = await apiClient.get(`${API_BASE}/${paperId}/chunks`);
  return response.data;
}
