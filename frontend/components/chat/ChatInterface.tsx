/**
 * # ChatInterface Component
 * 
 * ## What it does:
 * Main container for the "Chat with papers" feature. Orchestrates all chat-related
 * components. Manages chat state and API interactions. Allows users to ask questions
 * across multiple uploaded papers.
 * 
 * ## How it works:
 * - Uses useChat hook for state management
 * - Integrates with TanStack Query for API calls
 * - Handles message sending and receiving
 * - Manages selected papers for context
 * - Displays empty state when no papers uploaded
 * - Coordinates PaperSelector, MessageList, and MessageInput components
 * 
 * ## What to include:
 * - PaperSelector component (for multi-paper selection)
 * - MessageList component (displays chat history)
 * - MessageInput component (user input)
 * - Loading states during API calls
 * - Error handling and error display
 * - Empty state when no papers available (EmptyState component)
 * - Chat history persistence (from chatStore or API)
 * - Scroll to bottom on new messages
 * - Clear chat functionality
 */

