/**
 * # Chat Types
 * 
 * ## What it does:
 * TypeScript types for chat messages, citations, and chat-related data structures.
 * 
 * ## How it works:
 * - Exports TypeScript interfaces and types
 * - Matches backend chat response structure
 * - Used by chat components and hooks
 * 
 * ## What to include:
 * - Message interface: id, role (user/assistant), content, citations, timestamp
 * - Citation interface: paperId, paperName, pageNumber, chunkText (optional)
 * - ChatResponse interface: message, citations, retrievedChunks
 * - Conversation interface: id, messages, createdAt, updatedAt
 * - MessageRole enum: user, assistant
 */

