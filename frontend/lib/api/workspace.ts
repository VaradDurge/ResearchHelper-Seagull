import { apiClient } from "./client";
import type {
  Workspace,
  WorkspaceListResponse,
  InvitationResponse,
  InvitationListResponse,
  InvitationAcceptResponse,
  InvitationEmailStatusResponse,
  PendingInvite,
  WorkspaceMember,
} from "@/types/workspace";

const API_BASE = "/api/v1/workspaces";

export async function getWorkspaces(): Promise<WorkspaceListResponse> {
  const response = await apiClient.get<WorkspaceListResponse>(API_BASE);
  return response.data;
}

export async function getActiveWorkspace(): Promise<Workspace> {
  const response = await apiClient.get<Workspace>(`${API_BASE}/active`);
  return response.data;
}

export async function createWorkspace(name: string): Promise<Workspace> {
  const response = await apiClient.post<Workspace>(API_BASE, { name });
  return response.data;
}

export async function switchWorkspace(workspaceId: string): Promise<Workspace> {
  const response = await apiClient.post<Workspace>(
    `${API_BASE}/${workspaceId}/switch`
  );
  return response.data;
}

export async function renameWorkspace(
  workspaceId: string,
  name: string
): Promise<Workspace> {
  const response = await apiClient.put<Workspace>(`${API_BASE}/${workspaceId}`, {
    name,
  });
  return response.data;
}

// ── Invitation APIs ─────────────────────────────────────────────

export async function inviteToWorkspace(
  workspaceId: string,
  email: string,
  options?: { deliveryMethod?: "email" | "link" }
): Promise<InvitationResponse> {
  const response = await apiClient.post<InvitationResponse>(
    `${API_BASE}/${workspaceId}/invite`,
    { email, delivery_method: options?.deliveryMethod ?? "email" }
  );
  return response.data;
}

export async function acceptInvitation(
  token: string
): Promise<InvitationAcceptResponse> {
  const response = await apiClient.post<InvitationAcceptResponse>(
    `${API_BASE}/invitations/${token}/accept`
  );
  return response.data;
}

export async function getInvitations(
  workspaceId: string
): Promise<InvitationListResponse> {
  const response = await apiClient.get<InvitationListResponse>(
    `${API_BASE}/${workspaceId}/invitations`
  );
  return response.data;
}

export async function revokeInvitation(invitationId: string): Promise<void> {
  await apiClient.delete(`${API_BASE}/invitations/${invitationId}`);
}

export async function getMyPendingInvitations(): Promise<PendingInvite[]> {
  const response = await apiClient.get<{ invitations: PendingInvite[] }>(
    `${API_BASE}/invitations/mine`
  );
  return response.data.invitations;
}

export async function getInvitationEmailStatus(
  invitationId: string
): Promise<InvitationEmailStatusResponse> {
  const response = await apiClient.get<InvitationEmailStatusResponse>(
    `${API_BASE}/invitations/${invitationId}/email-status`
  );
  return response.data;
}

// ── Members (collaborators list & remove) ─────────────────────────────

export async function getWorkspaceMembers(
  workspaceId: string
): Promise<WorkspaceMember[]> {
  const response = await apiClient.get<{ members: WorkspaceMember[] }>(
    `${API_BASE}/${workspaceId}/members`
  );
  return response.data.members;
}

export async function removeWorkspaceMember(
  workspaceId: string,
  memberUserId: string
): Promise<void> {
  await apiClient.delete(
    `${API_BASE}/${workspaceId}/members/${memberUserId}`
  );
}
