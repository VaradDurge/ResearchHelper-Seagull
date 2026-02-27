"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useWebSocket, useWSEvent } from "./WebSocketProvider";

const TYPING_DEBOUNCE_MS = 2000;

/**
 * Manages typing indicators for the chat feature.
 *
 * Returns:
 *  - typingUsers: array of user_ids currently typing
 *  - onTyping(): call when the local user types (debounced start/stop)
 */
export function useTypingIndicator() {
  const { sendEvent } = useWebSocket();
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const isTypingRef = useRef(false);

  useWSEvent("typing_start", (e) => {
    const uid: string = e.payload?.user_id;
    if (uid) setTypingUsers((prev) => (prev.includes(uid) ? prev : [...prev, uid]));
  });

  useWSEvent("typing_stop", (e) => {
    const uid: string = e.payload?.user_id;
    if (uid) setTypingUsers((prev) => prev.filter((id) => id !== uid));
  });

  const sendStop = useCallback(() => {
    if (isTypingRef.current) {
      isTypingRef.current = false;
      sendEvent({ type: "typing_stop" });
    }
  }, [sendEvent]);

  const onTyping = useCallback(() => {
    if (!isTypingRef.current) {
      isTypingRef.current = true;
      sendEvent({ type: "typing_start" });
    }
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(sendStop, TYPING_DEBOUNCE_MS);
  }, [sendEvent, sendStop]);

  useEffect(() => {
    return () => {
      clearTimeout(timerRef.current);
      sendStop();
    };
  }, [sendStop]);

  return { typingUsers, onTyping };
}
