"use client";

import { useWebSocket, type PresenceUser } from "./WebSocketProvider";

/**
 * Returns the list of online users in the current workspace (from WebSocket presence).
 * The current user is excluded from the list automatically by the backend.
 */
export function usePresence(): PresenceUser[] {
  const { presence } = useWebSocket();
  return presence;
}
