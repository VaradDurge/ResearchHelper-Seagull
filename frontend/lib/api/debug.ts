/**
 * Debug / maintenance API for intelligence graph.
 * Exposes endpoints to rebuild intelligence for all papers in the current workspace.
 */
import { apiClient } from "./client";

interface RebuildIntelligenceResponse {
  papers_processed: number;
  success_count: number;
  failure_count: number;
}

export async function rebuildIntelligenceForWorkspace(): Promise<RebuildIntelligenceResponse> {
  const response = await apiClient.post<RebuildIntelligenceResponse>("/api/v1/debug/rebuild-intelligence");
  return response.data;
}

