"""
# Chat Service

## What it does:
Service layer for chat operations. Orchestrates RAG pipeline for chat, manages
conversations, and handles chat history.

## How it works:
- Uses RAG pipeline to generate answers
- Manages conversation state
- Stores chat history in database
- Handles citation extraction and formatting

## What to include:
- send_message(message: str, paper_ids: List[str], conversation_id: str, user_id: str) -> ChatResponse
  - Calls RAG pipeline with message and paper_ids
  - Stores message and response in database
  - Returns answer with citations
  
- get_chat_history(conversation_id: str, limit: int, offset: int) -> List[Message]
  - Retrieves chat history from database
  - Returns messages with citations
  
- create_conversation(name: str, workspace_id: str, user_id: str) -> Conversation
  - Creates new conversation
  - Returns conversation object
  
- get_conversations(workspace_id: str, user_id: str) -> List[Conversation]
  - Lists conversations for user in workspace
  
- Uses RAG module for answer generation
- Handles streaming responses (optional)
"""

