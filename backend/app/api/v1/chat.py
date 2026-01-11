"""
# Chat API Endpoints

## What it does:
FastAPI route handlers for chat operations. Handles RAG-based chat with papers,
message sending, and chat history.

## How it works:
- Defines API endpoints for chat operations
- Uses dependency injection for database session and authentication
- Calls chat_service for business logic
- Returns chat responses with citations
- Supports streaming (optional, using Server-Sent Events or WebSocket)

## What to include:
- POST /chat - Send chat message
  - Request body: message (string), paper_ids (List[str]), conversation_id (optional)
  - Response: ChatResponse with answer, citations, retrieved_chunks
  - Calls: chat_service.send_message() -> uses RAG pipeline
  - Optional: Streaming response using StreamingResponse
  
- GET /chat/history - Get chat history
  - Query params: conversation_id (optional), limit, offset
  - Response: List[MessageResponse]
  - Calls: chat_service.get_chat_history()
  
- POST /chat/conversations - Create new conversation
  - Request body: name (optional)
  - Response: ConversationResponse
  - Calls: chat_service.create_conversation()
  
- GET /chat/conversations - List conversations
  - Query params: workspace_id (from auth)
  - Response: List[ConversationResponse]
  - Calls: chat_service.get_conversations()
"""

