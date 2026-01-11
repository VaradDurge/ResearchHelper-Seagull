/**
 * # Chat Store (Zustand)
 * 
 * ## What it does:
 * Zustand store for managing chat state: chat history, selected papers for chat,
 * current conversation ID, and chat-related client state.
 * 
 * ## How it works:
 * - Uses Zustand for state management
 * - Stores chat messages/history
 * - Stores selected papers for chat context
 * - Provides actions to update chat state
 * 
 * ## What to include:
 * - State: messages, selectedPaperIds, conversationId, isStreaming
 * - Actions: addMessage, clearMessages, setSelectedPapers, setConversationId
 * - Persistence (optional, to maintain chat history across sessions)
 * - TypeScript types for store state and actions
 */

