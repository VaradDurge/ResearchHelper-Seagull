/**
 * # usePapers Hook
 * 
 * ## What it does:
 * Custom React hook for managing papers. Handles fetching papers list, uploading
 * papers, deleting papers, and paper-related operations.
 * 
 * ## How it works:
 * - Uses TanStack Query for fetching papers
 * - Uses mutations for upload/delete operations
 * - Invalidates queries after mutations
 * - Integrates with workspace context
 * 
 * ## What to include:
 * - State: papers, isLoading, error
 * - Functions: uploadPaper, deletePaper, refetchPapers
 * - TanStack Query: useQuery for papers list, useMutation for upload/delete
 * - Workspace filtering (only papers in current workspace)
 * - Optimistic updates for better UX
 * - TypeScript return type
 */

