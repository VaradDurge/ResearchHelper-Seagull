/**
 * Graph API - global knowledge graph of papers and Research Intelligence Graph.
 * Pass workspaceId to ensure the request uses that workspace (overrides localStorage).
 */
import { apiClient } from "./client";
import type { GraphResponse, IntelligenceGraphResponse } from "@/types/graph";

const API_BASE = "/api/v1/graph";

function workspaceHeaders(workspaceId: string) {
  return { headers: { "X-Workspace-Id": workspaceId } as Record<string, string> };
}

export async function getGraphWorkspace(workspaceId?: string): Promise<GraphResponse> {
  const config = workspaceId ? workspaceHeaders(workspaceId) : undefined;
  const response = await apiClient.get<GraphResponse>(`${API_BASE}/workspace`, config);
  return response.data;
}

export async function getGraphWorkspaceIntelligence(workspaceId?: string): Promise<IntelligenceGraphResponse> {
  const config = workspaceId ? workspaceHeaders(workspaceId) : undefined;
  const response = await apiClient.get<IntelligenceGraphResponse>(`${API_BASE}/workspace/intelligence`, config);
  return response.data;
}
