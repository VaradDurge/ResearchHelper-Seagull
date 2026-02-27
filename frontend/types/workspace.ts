export interface Workspace {
  id: string;
  name: string;
  user_id: string;
  owner_id: string;
  collaborators: string[];
  is_shared: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceListResponse {
  workspaces: Workspace[];
  total: number;
}

export interface InvitationResponse {
  id: string;
  workspace_id: string;
  inviter_id: string;
  invitee_email: string;
  invite_link?: string | null;
  status: "pending" | "accepted" | "expired" | "revoked";
  created_at: string;
  expires_at: string;
}

export interface InvitationListResponse {
  invitations: InvitationResponse[];
  total: number;
}

export interface InvitationAcceptResponse {
  workspace: Workspace;
  message: string;
}

export interface PendingInvite {
  invitation_id: string;
  token: string;
  workspace_id: string;
  workspace_name: string;
  inviter_name: string;
  inviter_picture: string;
  created_at: string;
}

export interface InvitationEmailStatusResponse {
  invitation_id: string;
  provider_email_id?: string | null;
  provider_status: string;
  last_event?: string | null;
  checked_at: string;
  raw?: Record<string, unknown> | null;
}

export interface WorkspaceMember {
  user_id: string;
  name: string;
  email: string;
  picture: string;
  role: "owner" | "collaborator";
}
