"""
Chat API Endpoints
Minimal RAG-based chat endpoint with real-time broadcast.
"""
from fastapi import APIRouter, HTTPException, Depends

from app.api.dependencies import get_current_user_id, get_current_workspace_id
from app.models.schemas import ChatMessageRequest, ChatResponse
from app.services.chat_service import send_message
from app.services.papers_service import get_paper_ids_for_workspace
from app.core.ws_manager import manager

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    payload: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id),
    workspace_id: str = Depends(get_current_workspace_id),
):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    # Always scope to current workspace: never use client-sent paper_ids for RAG
    paper_ids = get_paper_ids_for_workspace(user_id, workspace_id)

    if not paper_ids:
        return ChatResponse(
            answer="No papers in this workspace yet. Upload a PDF or import a DOI first.",
            citations=[],
            retrieved_chunks=[],
            conversation_id=None,
        )

    result = send_message(
        message=payload.message,
        paper_ids=paper_ids,
        conversation_id=payload.conversation_id,
        user_id=user_id,
        workspace_id=workspace_id,
    )

    await manager.broadcast(
        workspace_id,
        {
            "type": "new_message",
            "payload": {
                "user_id": user_id,
                "message": payload.message,
                "answer": result.answer,
                "conversation_id": result.conversation_id,
                "citations": [c.model_dump() for c in result.citations],
            },
        },
        exclude_user=user_id,
    )

    return result
