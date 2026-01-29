"""
Chat Service
Minimal chat service for RAG-based answers.
"""
from typing import List, Optional

from app.core.rag import retrieve, generate_answer
from app.models.schemas import ChatResponse, Citation, MessageRole
from app.services.conversation_service import (
    get_or_create_conversation,
    add_message,
)


def send_message(
    message: str,
    paper_ids: Optional[List[str]] = None,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> ChatResponse:
    """Generate a response grounded in retrieved chunks."""
    # Get or create conversation
    conv_id = None
    if user_id:
        conv_id = get_or_create_conversation(conversation_id, user_id, message)
        # Save user message
        add_message(conv_id, user_id, MessageRole.USER, message)

    # Generate answer
    retrieved = retrieve(message, paper_ids=paper_ids, top_k=5, user_id=user_id)
    rag_response = generate_answer(message, retrieved)

    # Convert citations
    citations = [
        Citation(
            paper_id=c["paper_id"],
            paper_title=c["paper_title"],
            page_number=c["page_number"],
            chunk_index=c["chunk_index"],
            text=c["text"],
        )
        for c in rag_response.citations
    ]

    # Save assistant message
    if user_id and conv_id:
        add_message(conv_id, user_id, MessageRole.ASSISTANT, rag_response.answer, citations)

    return ChatResponse(
        answer=rag_response.answer,
        citations=citations,
        retrieved_chunks=rag_response.retrieved_chunks,
        conversation_id=conv_id,
    )

