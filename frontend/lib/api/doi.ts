/**
 * # DOI Lookup API Functions
 *
 * API functions for DOI lookup operations.
 */
import { apiClient } from "./client";

const API_BASE = "/api/v1/doi";

export interface DoiLookupRequest {
  dois: string[];
}

export interface DoiLookupResult {
  doi: string;
  title?: string;
  authors: string[];
  url?: string;
  source?: string;
  error?: string;
}

export interface DoiLookupResponse {
  results: DoiLookupResult[];
}

export async function lookupDois(dois: string[]): Promise<DoiLookupResponse> {
  const response = await apiClient.post<DoiLookupResponse>(`${API_BASE}/lookup`, {
    dois,
  });

  return response.data;
}
