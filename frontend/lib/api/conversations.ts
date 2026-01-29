/**
 * Conversations API Functions
 */
import { apiClient } from "./client";

const API_BASE = "/api/v1/conversations";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Array<{
    paper_id: string;
    paper_title: string;
    page_number: number;
    chunk_index: number;
    text: string;
  }>;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ConversationListResponse {
  conversations: Conversation[];
  total: number;
}

export async function getConversations(): Promise<ConversationListResponse> {
  const response = await apiClient.get<ConversationListResponse>(API_BASE);
  return response.data;
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  const response = await apiClient.get<ConversationDetail>(`${API_BASE}/${id}`);
  return response.data;
}

export async function deleteConversation(id: string): Promise<void> {
  await apiClient.delete(`${API_BASE}/${id}`);
}
