/**
 * # Workspace Store (Zustand)
 * 
 * ## What it does:
 * Zustand store for managing workspace state: current workspace, papers list,
 * and workspace-related client state.
 * 
 * ## How it works:
 * - Uses Zustand for state management
 * - Stores current workspace ID and data
 * - Stores papers list (can be synced with TanStack Query)
 * - Provides actions to update workspace state
 * 
 * ## What to include:
 * - State: currentWorkspaceId, currentWorkspace, papers (optional, can use TanStack Query instead)
 * - Actions: setWorkspace, setPapers, clearWorkspace
 * - Persistence (optional, using Zustand persist middleware)
 * - TypeScript types for store state and actions
 */

