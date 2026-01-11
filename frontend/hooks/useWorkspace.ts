/**
 * # useWorkspace Hook
 * 
 * ## What it does:
 * Custom React hook for managing workspace state and operations. Handles fetching
 * workspaces, switching workspace, creating workspace.
 * 
 * ## How it works:
 * - Uses TanStack Query for fetching workspaces
 * - Uses mutations for create/update/switch operations
 * - Integrates with workspaceStore (Zustand)
 * - Updates global workspace state
 * 
 * ## What to include:
 * - State: workspaces, currentWorkspace, isLoading, error
 * - Functions: createWorkspace, switchWorkspace, updateWorkspace
 * - TanStack Query: useQuery for workspaces, useMutation for operations
 * - Integration with workspaceStore
 * - TypeScript return type
 */

