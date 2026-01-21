"""
Chat Service
Minimal chat service for RAG-based answers.
"""
from typing import List, Optional

from app.core.rag import retrieve, generate_answer
from app.models.schemas import ChatResponse


def send_message(
    message: str,
    paper_ids: Optional[List[str]] = None,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> ChatResponse:
    """Generate a response grounded in retrieved chunks."""
    retrieved = retrieve(message, paper_ids=paper_ids, top_k=5)
    rag_response = generate_answer(message, retrieved)
    return ChatResponse(
        answer=rag_response.answer,
        citations=rag_response.citations,
        retrieved_chunks=rag_response.retrieved_chunks,
    )

