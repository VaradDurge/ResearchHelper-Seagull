"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { usePathname } from "next/navigation";
import { API_URL } from "@/lib/api/client";

// ── Types ───────────────────────────────────────────────────────────

export interface WSEvent {
  type: string;
  payload?: any;
}

export interface PresenceUser {
  user_id: string;
  name: string;
  picture: string;
  current_page: string;
  online: boolean;
}

type EventCallback = (event: WSEvent) => void;

interface WebSocketContextValue {
  connected: boolean;
  sendEvent: (event: WSEvent) => void;
  subscribe: (type: string, cb: EventCallback) => () => void;
  presence: PresenceUser[];
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

// ── Provider ────────────────────────────────────────────────────────

const WS_BASE = API_URL.replace(/^http/, "ws");
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const HEARTBEAT_INTERVAL_MS = 25000;

interface Props {
  workspaceId: string | null;
  children: ReactNode;
}

export function WebSocketProvider({ workspaceId, children }: Props) {
  const wsRef = useRef<WebSocket | null>(null);
  const listenersRef = useRef<Map<string, Set<EventCallback>>>(new Map());
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const heartbeatTimer = useRef<ReturnType<typeof setInterval>>();
  const retryCount = useRef(0);

  const [connected, setConnected] = useState(false);
  const [presence, setPresence] = useState<PresenceUser[]>([]);

  const pathname = usePathname();
  const prevPathRef = useRef(pathname);

  const dispatch = useCallback((event: WSEvent) => {
    const cbs = listenersRef.current.get(event.type);
    if (cbs) cbs.forEach((cb) => cb(event));
  }, []);

  const sendEvent = useCallback((event: WSEvent) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(event));
    }
  }, []);

  const subscribe = useCallback((type: string, cb: EventCallback) => {
    if (!listenersRef.current.has(type)) {
      listenersRef.current.set(type, new Set());
    }
    listenersRef.current.get(type)!.add(cb);
    return () => {
      listenersRef.current.get(type)?.delete(cb);
    };
  }, []);

  // Send page change on navigation
  useEffect(() => {
    if (pathname !== prevPathRef.current) {
      prevPathRef.current = pathname;
      sendEvent({ type: "presence_page", page: pathname } as any);
    }
  }, [pathname, sendEvent]);

  // Main connection effect
  useEffect(() => {
    if (!workspaceId) return;
    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    if (!token) return;

    let destroyed = false;

    const connect = () => {
      if (destroyed) return;

      const url = `${WS_BASE}/api/v1/ws/${workspaceId}?token=${token}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retryCount.current = 0;
        ws.send(JSON.stringify({ type: "presence_page", page: pathname }));

        heartbeatTimer.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }));
          }
        }, HEARTBEAT_INTERVAL_MS);
      };

      ws.onmessage = (e) => {
        try {
          const event: WSEvent = JSON.parse(e.data);
          if (event.type === "presence_update") {
            setPresence(event.payload ?? []);
          }
          dispatch(event);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        clearInterval(heartbeatTimer.current);
        if (!destroyed) {
          const delay = Math.min(
            RECONNECT_BASE_MS * 2 ** retryCount.current,
            RECONNECT_MAX_MS
          );
          retryCount.current += 1;
          reconnectTimer.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      destroyed = true;
      clearTimeout(reconnectTimer.current);
      clearInterval(heartbeatTimer.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnected(false);
      setPresence([]);
    };
  }, [workspaceId, dispatch, pathname]);

  return (
    <WebSocketContext.Provider value={{ connected, sendEvent, subscribe, presence }}>
      {children}
    </WebSocketContext.Provider>
  );
}

// ── Hooks ───────────────────────────────────────────────────────────

export function useWebSocket() {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error("useWebSocket must be used within WebSocketProvider");
  return ctx;
}

export function useWSEvent(type: string, callback: EventCallback) {
  const { subscribe } = useWebSocket();
  const cbRef = useRef(callback);
  cbRef.current = callback;

  useEffect(() => {
    return subscribe(type, (e) => cbRef.current(e));
  }, [type, subscribe]);
}
