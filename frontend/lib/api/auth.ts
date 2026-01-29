/**
 * Auth API Functions
 */
import { apiClient } from "./client";

const API_BASE = "/api/v1/auth";

export interface User {
  user_id: string;
  email?: string;
  name?: string;
  picture?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export async function loginWithGoogle(idToken: string): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>(`${API_BASE}/google`, {
    id_token: idToken,
  });
  return response.data;
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>(`${API_BASE}/me`);
  return response.data;
}
