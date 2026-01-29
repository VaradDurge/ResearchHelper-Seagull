"""
Conversations API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends

from app.api.dependencies import get_current_user_id
from app.models.schemas import (
    ConversationListResponse,
    ConversationDetailResponse,
)
from app.services.conversation_service import (
    get_conversations_by_user,
    get_conversation_with_messages,
    delete_conversation,
)

router = APIRouter()


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(user_id: str = Depends(get_current_user_id)):
    """List all conversations for the current user."""
    conversations = get_conversations_by_user(user_id)
    return ConversationListResponse(conversations=conversations, total=len(conversations))


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str, user_id: str = Depends(get_current_user_id)
):
    """Get a conversation with all messages."""
    conversation = get_conversation_with_messages(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/{conversation_id}")
async def remove_conversation(
    conversation_id: str, user_id: str = Depends(get_current_user_id)
):
    """Delete a conversation."""
    success = delete_conversation(conversation_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted successfully"}
