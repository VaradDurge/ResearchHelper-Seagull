"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  getMyPendingInvitations,
  acceptInvitation,
  switchWorkspace,
} from "@/lib/api/workspace";
import type { PendingInvite } from "@/types/workspace";

const POLL_INTERVAL_MS = 10_000;

export function InvitationNotification() {
  const [invites, setInvites] = useState<PendingInvite[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [joining, setJoining] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  const poll = useCallback(async () => {
    try {
      const list = await getMyPendingInvitations();
      setInvites(list);
    } catch {
      // silently ignore polling errors
    }
  }, []);

  useEffect(() => {
    poll();
    timerRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(timerRef.current);
  }, [poll]);

  const handleJoin = async (invite: PendingInvite) => {
    setJoining(invite.invitation_id);
    setErrors((prev) => {
      const next = { ...prev };
      delete next[invite.invitation_id];
      return next;
    });

    try {
      const result = await acceptInvitation(invite.token);
      const wsId = result.workspace.id;
      localStorage.setItem("active_workspace_id", wsId);
      try {
        await switchWorkspace(wsId);
      } catch {
        // best-effort
      }
      window.location.href = "/chat";
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail || err?.message || "Failed to accept invitation";
      setErrors((prev) => ({ ...prev, [invite.invitation_id]: msg }));
      setJoining(null);
    }
  };

  const handleDismiss = (id: string) => {
    setDismissed((prev) => new Set(prev).add(id));
  };

  const visible = invites.filter((i) => !dismissed.has(i.invitation_id));
  if (visible.length === 0) return null;

  return (
    <div className="fixed right-5 top-5 z-[100] flex flex-col gap-3 pointer-events-none">
      {visible.map((inv) => {
        const errMsg = errors[inv.invitation_id];
        return (
          <div
            key={inv.invitation_id}
            className="pointer-events-auto flex items-start gap-3 rounded-xl border border-border/60 bg-card/95 px-4 py-3 shadow-[0_8px_30px_rgba(0,0,0,0.45)] backdrop-blur-xl animate-in slide-in-from-top-2 fade-in duration-300"
            style={{ minWidth: 320, maxWidth: 400 }}
          >
            <Avatar className="mt-0.5 h-9 w-9 shrink-0">
              <AvatarImage src={inv.inviter_picture} alt={inv.inviter_name} />
              <AvatarFallback>
                {inv.inviter_name?.[0]?.toUpperCase() || "?"}
              </AvatarFallback>
            </Avatar>

            <div className="flex-1 min-w-0">
              <p className="text-sm leading-snug">
                <span className="font-semibold text-foreground">
                  {inv.inviter_name}
                </span>{" "}
                <span className="text-muted-foreground">invited you to</span>{" "}
                <span className="font-semibold text-foreground">
                  {inv.workspace_name}
                </span>
              </p>
              {errMsg && (
                <p className="mt-1 text-xs text-destructive">{errMsg}</p>
              )}
              <div className="mt-2 flex gap-2">
                <Button
                  size="sm"
                  className="h-7 rounded-lg px-4 text-xs font-semibold"
                  onClick={() => handleJoin(inv)}
                  disabled={joining === inv.invitation_id}
                >
                  {joining === inv.invitation_id ? "Joining..." : "Join"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 rounded-lg px-3 text-xs text-muted-foreground"
                  onClick={() => handleDismiss(inv.invitation_id)}
                >
                  Dismiss
                </Button>
              </div>
            </div>

            <button
              onClick={() => handleDismiss(inv.invitation_id)}
              className="shrink-0 rounded-md p-1 text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
