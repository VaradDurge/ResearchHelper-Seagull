/**
 * # Cross Eval API Functions
 *
 * API functions for cross-evaluation operations.
 */
import { apiClient } from "./client";
import type { Citation } from "./chat";

const API_BASE = "/api/v1/cross-eval";

export interface CrossEvalRequest {
  message: string;
  paper_ids?: string[];
  top_k?: number;
}

export interface CrossEvalResult {
  paper_id: string;
  paper_title: string;
  answer: string;
}

export interface CrossEvalResponse {
  answer: string;
  citations: Citation[];
  per_paper: CrossEvalResult[];
}

export async function sendCrossEval(
  message: string,
  paperIds?: string[],
  topK = 5
): Promise<CrossEvalResponse> {
  const response = await apiClient.post<CrossEvalResponse>(API_BASE, {
    message,
    paper_ids: paperIds,
    top_k: topK,
  });

  return response.data;
}
