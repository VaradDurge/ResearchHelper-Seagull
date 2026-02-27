"""
WebSocket Connection Manager - Manages per-workspace real-time connections.
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by workspace_id."""

    def __init__(self):
        # workspace_id -> {user_id -> WebSocket}
        self._connections: Dict[str, Dict[str, WebSocket]] = {}
        # workspace_id -> {user_id -> presence_info}
        self._presence: Dict[str, Dict[str, dict]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        ws: WebSocket,
        workspace_id: str,
        user_id: str,
        user_info: Optional[dict] = None,
    ):
        await ws.accept()
        async with self._lock:
            if workspace_id not in self._connections:
                self._connections[workspace_id] = {}
                self._presence[workspace_id] = {}

            old_ws = self._connections[workspace_id].get(user_id)
            if old_ws:
                try:
                    await old_ws.close(code=4001, reason="new_connection")
                except Exception:
                    pass

            self._connections[workspace_id][user_id] = ws
            self._presence[workspace_id][user_id] = {
                "user_id": user_id,
                "name": (user_info or {}).get("name", ""),
                "picture": (user_info or {}).get("picture", ""),
                "current_page": "/chat",
                "online": True,
            }

        logger.info(f"WS connected: user={user_id} workspace={workspace_id}")

        await self.broadcast(
            workspace_id,
            {
                "type": "presence_update",
                "payload": self.get_presence(workspace_id),
            },
        )

    async def disconnect(self, workspace_id: str, user_id: str):
        async with self._lock:
            ws_map = self._connections.get(workspace_id, {})
            ws_map.pop(user_id, None)
            pres_map = self._presence.get(workspace_id, {})
            pres_map.pop(user_id, None)

            if not ws_map:
                self._connections.pop(workspace_id, None)
                self._presence.pop(workspace_id, None)

        logger.info(f"WS disconnected: user={user_id} workspace={workspace_id}")

        if workspace_id in self._connections:
            await self.broadcast(
                workspace_id,
                {
                    "type": "presence_update",
                    "payload": self.get_presence(workspace_id),
                },
            )

    async def broadcast(
        self,
        workspace_id: str,
        event: dict,
        exclude_user: Optional[str] = None,
    ):
        """Send an event to all connections in a workspace."""
        ws_map = self._connections.get(workspace_id, {})
        data = json.dumps(event)
        dead: list[str] = []

        for uid, ws in ws_map.items():
            if uid == exclude_user:
                continue
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(uid)

        for uid in dead:
            await self.disconnect(workspace_id, uid)

    async def send_personal(
        self,
        workspace_id: str,
        user_id: str,
        event: dict,
    ):
        ws = self._connections.get(workspace_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                await self.disconnect(workspace_id, user_id)

    def get_presence(self, workspace_id: str) -> list[dict]:
        return list(self._presence.get(workspace_id, {}).values())

    def update_presence(self, workspace_id: str, user_id: str, data: dict):
        pres = self._presence.get(workspace_id, {}).get(user_id)
        if pres:
            pres.update(data)

    def get_online_users(self, workspace_id: str) -> list[str]:
        return list(self._connections.get(workspace_id, {}).keys())

    def is_user_connected(self, workspace_id: str, user_id: str) -> bool:
        return user_id in self._connections.get(workspace_id, {})


manager = ConnectionManager()
