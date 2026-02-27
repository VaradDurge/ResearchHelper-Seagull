"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Settings, Send, Loader2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { getCurrentUser, type User } from "@/lib/api/auth";
import { inviteToWorkspace, getInvitationEmailStatus } from "@/lib/api/workspace";
import { useWorkspace } from "@/store/workspaceStore";
import { CollaboratorAvatars } from "./CollaboratorAvatars";
import { CollaboratorsDialog } from "./CollaboratorsDialog";

export function Header() {
  const { activeWorkspace } = useWorkspace();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteStatus, setInviteStatus] = useState<"idle" | "success" | "error">("idle");
  const [inviteError, setInviteError] = useState("");
  const [inviteDelivery, setInviteDelivery] = useState<string>("");
  const [inviteDeliveryReason, setInviteDeliveryReason] = useState<string>("");
  const [linkCopied, setLinkCopied] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  const extractProviderReason = (raw?: Record<string, unknown> | null): string => {
    if (!raw || typeof raw !== "object") return "";
    const candidates = [
      "reason",
      "error",
      "message",
      "last_error",
      "failure_reason",
      "bounce_reason",
      "rejection_reason",
    ];
    for (const key of candidates) {
      const value = raw[key];
      if (typeof value === "string" && value.trim()) return value.trim();
    }
    const errorObj = raw["error"];
    if (errorObj && typeof errorObj === "object") {
      const nestedMessage = (errorObj as Record<string, unknown>)["message"];
      if (typeof nestedMessage === "string" && nestedMessage.trim()) return nestedMessage.trim();
    }
    return "";
  };

  useEffect(() => {
    const cached = localStorage.getItem("auth_user");
    if (cached) {
      try {
        setUser(JSON.parse(cached));
      } catch {
        localStorage.removeItem("auth_user");
      }
    }
    getCurrentUser()
      .then((me) => {
        setUser(me);
        localStorage.setItem("auth_user", JSON.stringify(me));
      })
      .catch(() => {});
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    window.location.assign("/chat");
  };

  const fallbackInitial =
    (user?.name?.trim()?.[0] || user?.email?.trim()?.[0] || "U").toUpperCase();

  const handleSendInvite = async () => {
    if (!inviteEmail.trim() || inviteLoading || !activeWorkspace) return;

    setInviteLoading(true);
    setInviteStatus("idle");
    setInviteError("");
    setInviteDelivery("");
    setInviteDeliveryReason("");

    try {
      const created = await inviteToWorkspace(activeWorkspace.id, inviteEmail.trim());
      setInviteStatus("success");
      // Best-effort provider status check so users can see if it bounced/delivered.
      setTimeout(async () => {
        try {
          const status = await getInvitationEmailStatus(created.id);
          const eventSuffix = status.last_event ? ` (${status.last_event})` : "";
          setInviteDelivery(`${status.provider_status}${eventSuffix}`);
          setInviteDeliveryReason(extractProviderReason(status.raw));
        } catch {
          setInviteDelivery("status_unavailable");
          setInviteDeliveryReason("");
        }
      }, 1200);
      setTimeout(() => {
        setInviteEmail("");
        setInviteStatus("idle");
        setInviteDelivery("");
        setInviteDeliveryReason("");
        setInviteOpen(false);
      }, 3500);
    } catch (err: any) {
      setInviteStatus("error");
      setInviteError(
        err?.response?.data?.detail || err?.message || "Failed to send invitation"
      );
    } finally {
      setInviteLoading(false);
    }
  };

  const handleCopyInviteLink = async () => {
    if (!inviteEmail.trim() || inviteLoading || !activeWorkspace) return;

    setInviteLoading(true);
    setInviteStatus("idle");
    setInviteError("");
    setInviteDelivery("");
    setInviteDeliveryReason("");
    setLinkCopied(false);

    try {
      const created = await inviteToWorkspace(activeWorkspace.id, inviteEmail.trim(), {
        deliveryMethod: "link",
      });
      const link = created.invite_link;
      if (!link) throw new Error("Invite link is unavailable");
      await navigator.clipboard.writeText(link);
      setLinkCopied(true);
      setInviteStatus("success");
      setInviteDelivery("link_copied");
      setTimeout(() => {
        setInviteEmail("");
        setLinkCopied(false);
        setInviteStatus("idle");
        setInviteOpen(false);
      }, 2500);
    } catch (err: any) {
      setInviteStatus("error");
      setInviteError(
        err?.response?.data?.detail || err?.message || "Failed to copy invite link"
      );
    } finally {
      setInviteLoading(false);
    }
  };

  return (
    <header className="sticky top-0 z-50 flex h-14 items-center justify-between gap-4 bg-background px-6">
      <SidebarTrigger />
      <div className="flex items-center gap-4">
        <CollaboratorAvatars />

        {activeWorkspace && <CollaboratorsDialog />}

        <Popover open={inviteOpen} onOpenChange={setInviteOpen}>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Invite
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-72 p-3">
            <div className="space-y-3">
              <div className="space-y-1">
                <h4 className="text-sm font-medium">Invite collaborator</h4>
                <p className="text-xs text-muted-foreground">
                  Send an invitation email to collaborate on{" "}
                  <strong>{activeWorkspace?.name ?? "this workspace"}</strong>.
                </p>
              </div>
              <div className="flex gap-2">
                <Input
                  type="email"
                  placeholder="email@example.com"
                  value={inviteEmail}
                  onChange={(e) => {
                    setInviteEmail(e.target.value);
                    if (inviteStatus !== "idle") setInviteStatus("idle");
                  }}
                  onKeyDown={(e) => e.key === "Enter" && handleSendInvite()}
                  className="h-8 text-sm"
                />
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-8 px-3"
                  onClick={handleCopyInviteLink}
                  disabled={!inviteEmail.trim() || inviteLoading}
                >
                  Link
                </Button>
                <Button
                  size="sm"
                  className="h-8 px-3"
                  onClick={handleSendInvite}
                  disabled={!inviteEmail.trim() || inviteLoading}
                >
                  {inviteLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
              {inviteStatus === "success" && (
                <p className="text-xs text-green-600">Invitation sent!</p>
              )}
              {linkCopied && (
                <p className="text-xs text-green-600">Invite link copied to clipboard.</p>
              )}
              {inviteStatus === "error" && (
                <p className="text-xs text-destructive">
                  {inviteError || "Failed to send. Try again."}
                </p>
              )}
              {inviteStatus === "success" && inviteDelivery && (
                <p className="text-xs text-muted-foreground">
                  Email status: <span className="font-medium">{inviteDelivery}</span>
                </p>
              )}
              {inviteStatus === "success" && inviteDeliveryReason && (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  Provider reason: <span className="font-medium">{inviteDeliveryReason}</span>
                </p>
              )}
            </div>
          </PopoverContent>
        </Popover>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <Settings className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>Settings</DropdownMenuItem>
            <DropdownMenuItem>Preferences</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full">
              <Avatar>
                <AvatarImage src={user?.picture} alt={user?.name || "User"} />
                <AvatarFallback>{fallbackInitial}</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>Profile</DropdownMenuItem>
            <DropdownMenuItem onClick={handleLogout}>Logout</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
