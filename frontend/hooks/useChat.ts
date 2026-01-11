/**
 * # useChat Hook
 * 
 * ## What it does:
 * Custom React hook for managing chat state and API interactions. Handles sending
 * messages, receiving responses, managing chat history, and selected papers.
 * 
 * ## How it works:
 * - Uses TanStack Query for API calls
 * - Uses Zustand store for client state (optional)
 * - Manages message history
 * - Handles streaming responses (if implemented)
 * - Updates chat store with new messages
 * 
 * ## What to include:
 * - State: messages, selectedPapers, isLoading, error
 * - Functions: sendMessage, clearChat, selectPapers
 * - TanStack Query mutations and queries
 * - Message history management
 * - Citation extraction from responses
 * - Integration with chatStore (Zustand)
 * - TypeScript return type
 */

