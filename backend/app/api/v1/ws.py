"""
WebSocket endpoint for real-time collaboration.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.security import decode_access_token
from app.core.ws_manager import manager
from app.db.mongo import get_users_collection
from app.services.workspace_service import get_workspace_by_id

logger = logging.getLogger(__name__)

router = APIRouter()


def _authenticate_ws(token: str) -> str | None:
    """Validate JWT and return user_id, or None on failure."""
    try:
        payload = decode_access_token(token)
        return payload.get("sub")
    except Exception:
        return None


@router.websocket("/ws/{workspace_id}")
async def websocket_endpoint(
    ws: WebSocket,
    workspace_id: str,
    token: str = Query(...),
):
    user_id = _authenticate_ws(token)
    if not user_id:
        await ws.close(code=4001, reason="unauthorized")
        return

    workspace = get_workspace_by_id(workspace_id, user_id)
    if not workspace:
        await ws.close(code=4003, reason="workspace_not_found")
        return

    users = get_users_collection()
    user_doc = users.find_one({"user_id": user_id}) or {}
    user_info = {
        "name": user_doc.get("name", ""),
        "picture": user_doc.get("picture", ""),
        "email": user_doc.get("email", ""),
    }

    await manager.connect(ws, workspace_id, user_id, user_info)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await manager.send_personal(workspace_id, user_id, {"type": "pong"})

            elif msg_type == "presence_page":
                page = msg.get("page", "/chat")
                manager.update_presence(workspace_id, user_id, {"current_page": page})
                await manager.broadcast(
                    workspace_id,
                    {"type": "presence_update", "payload": manager.get_presence(workspace_id)},
                )

            elif msg_type == "typing_start":
                await manager.broadcast(
                    workspace_id,
                    {"type": "typing_start", "payload": {"user_id": user_id}},
                    exclude_user=user_id,
                )

            elif msg_type == "typing_stop":
                await manager.broadcast(
                    workspace_id,
                    {"type": "typing_stop", "payload": {"user_id": user_id}},
                    exclude_user=user_id,
                )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(f"WS error for user={user_id}: {exc}")
    finally:
        await manager.disconnect(workspace_id, user_id)
