/**
 * # Tools API Functions
 * Claim verification and other tools.
 */
import { apiClient } from "./client";
import { VERIFY_CLAIM, VERIFY_RECENT } from "./endpoints";

export interface ClaimVerifyRequest {
  claim: string;
  paper_ids?: string[] | null;
}

export interface ScoredEvidenceItem {
  evidence_score: number;
  classification: { classification: string; confidence: number; reason: string };
  similarity_score: number;
  paper_id: string;
  paper_title: string;
  page_number: number;
  chunk_index: number;
  text: string;
  score_components?: Record<string, number>;
}

export interface ClaimVerifyResponse {
  claim: string;
  support_count: number;
  contradict_count: number;
  neutral_count: number;
  evidence_count: number;
  confidence_score: number;
  confidence_label: string;
  evidence_strength: string;
  strongest_study_types: string[];
  guardrail_triggered: string | null;
  scored_evidence: ScoredEvidenceItem[];
}

export interface ClaimVerifyRunItem {
  run_id: string;
  user_id: string;
  user_name: string;
  claim: string;
  result: ClaimVerifyResponse;
  created_at: string;
}

export interface ClaimVerifyRecentResponse {
  runs: ClaimVerifyRunItem[];
  total: number;
}

export async function verifyClaim(
  claim: string,
  paperIds?: string[] | null
): Promise<ClaimVerifyResponse> {
  const response = await apiClient.post<ClaimVerifyResponse>(VERIFY_CLAIM, {
    claim,
    paper_ids: paperIds ?? null,
  });
  return response.data;
}

export async function getRecentVerifications(limit?: number): Promise<ClaimVerifyRecentResponse> {
  const params = limit != null ? { limit } : {};
  const response = await apiClient.get<ClaimVerifyRecentResponse>(VERIFY_RECENT, { params });
  return response.data;
}
