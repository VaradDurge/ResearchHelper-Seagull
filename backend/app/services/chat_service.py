"""
Chat Service
Minimal chat service for RAG-based answers.
"""
from typing import List, Optional, Dict
import re
import logging

from app.core.rag import (
    retrieve,
    generate_answer,
    is_question_list_request,
    list_questions,
)
from app.models.schemas import ChatResponse, Citation, MessageRole
from app.services.conversation_service import (
    get_or_create_conversation,
    add_message,
    get_recent_messages,
)

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 10


def _build_chat_history(conversation_id: Optional[str], user_id: Optional[str]) -> List[Dict[str, str]]:
    """Fetch recent messages and format them as OpenAI chat history."""
    if not conversation_id or not user_id:
        return []
    try:
        messages = get_recent_messages(conversation_id, user_id, limit=MAX_HISTORY_MESSAGES)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
    except Exception as e:
        logger.warning(f"Could not fetch chat history: {e}")
        return []


def send_message(
    message: str,
    paper_ids: Optional[List[str]] = None,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> ChatResponse:
    """Generate a response grounded in retrieved chunks."""
    conv_id = None
    if user_id and workspace_id:
        conv_id = get_or_create_conversation(conversation_id, user_id, workspace_id, message)
        # Save user message
        add_message(conv_id, user_id, MessageRole.USER, message)

    # Build chat history for context
    chat_history = _build_chat_history(conv_id, user_id)

    # Generate answer
    if is_question_list_request(message):
        page_match = re.search(r"\bpage\s+(\d+)\b", message.lower())
        page = int(page_match.group(1)) if page_match else 1
        page = max(1, page)
        page_size = 50
        offset = (page - 1) * page_size

        questions, citations, truncated = list_questions(
            paper_ids=paper_ids,
            workspace_id=workspace_id,
            max_questions=500,
            max_chunks=800,
            offset=offset,
            limit=page_size,
        )
        if questions:
            start_index = offset + 1
            lines = [
                f"{start_index + idx}. {question}"
                for idx, question in enumerate(questions)
            ]
            if truncated:
                lines.append("")
                lines.append("More questions exist. Say 'page 2' to see more.")
            answer = "\n".join(lines)
        else:
            answer = "Not found in the documents."

        response = ChatResponse(
            answer=answer,
            citations=[
                Citation(
                    paper_id=c["paper_id"],
                    paper_title=c["paper_title"],
                    page_number=c["page_number"],
                    chunk_index=c["chunk_index"],
                    text=c["text"],
                )
                for c in citations
            ],
            retrieved_chunks=[],
            conversation_id=conv_id,
        )
        if user_id and conv_id:
            add_message(conv_id, user_id, MessageRole.ASSISTANT, answer, response.citations)
        return response

    retrieved = retrieve(message, paper_ids=paper_ids, top_k=5, workspace_id=workspace_id)
    rag_response = generate_answer(message, retrieved, chat_history=chat_history)

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

