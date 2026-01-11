/**
 * # Chat API Functions
 * 
 * API functions for chat operations.
 */
import { apiClient } from "./client";

const API_BASE = "/api/v1/chat";

export interface ChatMessageRequest {
  message: string;
  paper_ids?: string[];
  conversation_id?: string;
}

export interface Citation {
  paper_id: string;
  paper_title: string;
  page_number: number;
  chunk_index: number;
  text: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  retrieved_chunks: any[];
}

export async function sendMessage(
  message: string,
  paperIds?: string[],
  conversationId?: string
): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>(API_BASE, {
    message,
    paper_ids: paperIds,
    conversation_id: conversationId,
  });
  
  return response.data;
}
