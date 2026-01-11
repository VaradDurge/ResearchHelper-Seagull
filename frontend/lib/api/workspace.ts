/**
 * # Workspace API Functions
 * 
 * ## What it does:
 * API functions for workspace operations: get workspaces, create workspace, switch workspace,
 * get current workspace, update workspace.
 * 
 * ## How it works:
 * - Exports functions for workspace operations
 * - Uses API client from client.ts
 * - Manages workspace context
 * 
 * ## What to include:
 * - getWorkspaces(): Promise<Workspace[]> - List all workspaces for user
 * - getCurrentWorkspace(): Promise<Workspace> - Get current active workspace
 * - createWorkspace(name: string): Promise<Workspace> - Create new workspace
 * - updateWorkspace(id: string, data: Partial<Workspace>): Promise<Workspace> - Update workspace
 * - deleteWorkspace(id: string): Promise<void> - Delete workspace
 * - switchWorkspace(id: string): Promise<void> - Switch active workspace
 * - TypeScript types: Workspace
 */

