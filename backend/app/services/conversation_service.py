"""
Conversation Service - MongoDB storage for chat history.
"""
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.db.mongo import get_conversations_collection, get_messages_collection
from app.models.schemas import (
    ConversationResponse,
    ConversationDetailResponse,
    Message,
    MessageRole,
    Citation,
)


def create_conversation(user_id: str, title: str = "New Chat") -> ConversationResponse:
    """Create a new conversation."""
    conversations = get_conversations_collection()
    now = datetime.now(timezone.utc)
    conv_id = str(uuid.uuid4())
    doc = {
        "conversation_id": conv_id,
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
    }
    conversations.insert_one(doc)
    return ConversationResponse(
        id=conv_id,
        title=title,
        user_id=user_id,
        created_at=now,
        updated_at=now,
        message_count=0,
    )


def get_or_create_conversation(
    conversation_id: Optional[str], user_id: str, first_message: str = ""
) -> str:
    """Get existing conversation or create new one."""
    if conversation_id:
        conversations = get_conversations_collection()
        existing = conversations.find_one(
            {"conversation_id": conversation_id, "user_id": user_id}
        )
        if existing:
            return conversation_id

    # Create new conversation with title from first message
    title = first_message[:50] + "..." if len(first_message) > 50 else first_message
    title = title or "New Chat"
    conv = create_conversation(user_id, title)
    return conv.id


def add_message(
    conversation_id: str,
    user_id: str,
    role: MessageRole,
    content: str,
    citations: Optional[List[Citation]] = None,
) -> Message:
    """Add a message to a conversation."""
    messages = get_messages_collection()
    conversations = get_conversations_collection()
    now = datetime.now(timezone.utc)
    msg_id = str(uuid.uuid4())

    doc = {
        "message_id": msg_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "role": role.value,
        "content": content,
        "citations": [c.model_dump() for c in (citations or [])],
        "created_at": now,
    }
    messages.insert_one(doc)

    # Update conversation
    conversations.update_one(
        {"conversation_id": conversation_id, "user_id": user_id},
        {"$set": {"updated_at": now}, "$inc": {"message_count": 1}},
    )

    return Message(
        id=msg_id,
        role=role,
        content=content,
        citations=citations or [],
        created_at=now,
    )


def get_conversations_by_user(user_id: str, limit: int = 50) -> List[ConversationResponse]:
    """Get all conversations for a user."""
    conversations = get_conversations_collection()
    docs = conversations.find({"user_id": user_id}).sort("updated_at", -1).limit(limit)
    result = []
    for doc in docs:
        result.append(
            ConversationResponse(
                id=doc["conversation_id"],
                title=doc["title"],
                user_id=doc["user_id"],
                created_at=doc["created_at"],
                updated_at=doc["updated_at"],
                message_count=doc.get("message_count", 0),
            )
        )
    return result


def get_conversation_with_messages(
    conversation_id: str, user_id: str
) -> Optional[ConversationDetailResponse]:
    """Get a conversation with all its messages."""
    conversations = get_conversations_collection()
    messages_col = get_messages_collection()

    conv = conversations.find_one(
        {"conversation_id": conversation_id, "user_id": user_id}
    )
    if not conv:
        return None

    msg_docs = messages_col.find(
        {"conversation_id": conversation_id, "user_id": user_id}
    ).sort("created_at", 1)

    messages = []
    for doc in msg_docs:
        citations = [Citation(**c) for c in doc.get("citations", [])]
        messages.append(
            Message(
                id=doc["message_id"],
                role=MessageRole(doc["role"]),
                content=doc["content"],
                citations=citations,
                created_at=doc["created_at"],
            )
        )

    return ConversationDetailResponse(
        id=conv["conversation_id"],
        title=conv["title"],
        user_id=conv["user_id"],
        created_at=conv["created_at"],
        updated_at=conv["updated_at"],
        message_count=conv.get("message_count", 0),
        messages=messages,
    )


def delete_conversation(conversation_id: str, user_id: str) -> bool:
    """Delete a conversation and all its messages."""
    conversations = get_conversations_collection()
    messages = get_messages_collection()

    result = conversations.delete_one(
        {"conversation_id": conversation_id, "user_id": user_id}
    )
    if result.deleted_count == 0:
        return False

    messages.delete_many({"conversation_id": conversation_id, "user_id": user_id})
    return True
