/**
 * # Workspace Types
 * 
 * ## What it does:
 * TypeScript types for workspaces, users, and workspace-related data structures.
 * 
 * ## How it works:
 * - Exports TypeScript interfaces and types
 * - Matches backend models
 * - Used by workspace components and hooks
 * 
 * ## What to include:
 * - Workspace interface: id, name, description, createdAt, updatedAt, userId, paperCount
 * - User interface: id, email, name, avatar (optional)
 * - WorkspaceMember interface: userId, workspaceId, role, joinedAt
 * - WorkspaceRole enum: owner, member, viewer
 * - WorkspaceInvite interface: id, workspaceId, email, token, expiresAt
 */

