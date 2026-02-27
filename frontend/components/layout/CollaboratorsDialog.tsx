"use client";

import { useEffect, useState } from "react";
import { Users, UserMinus, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { getWorkspaceMembers, removeWorkspaceMember } from "@/lib/api/workspace";
import { useWorkspace } from "@/store/workspaceStore";
import type { WorkspaceMember } from "@/types/workspace";

export function CollaboratorsDialog() {
  const { activeWorkspace } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [loading, setLoading] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isOwner = (() => {
    if (!activeWorkspace?.owner_id || typeof window === "undefined") return false;
    try {
      const u = localStorage.getItem("auth_user");
      if (!u) return false;
      const user = JSON.parse(u) as { user_id?: string };
      return user?.user_id === activeWorkspace.owner_id;
    } catch {
      return false;
    }
  })();

  useEffect(() => {
    if (!open || !activeWorkspace?.id) return;
    setLoading(true);
    setError(null);
    getWorkspaceMembers(activeWorkspace.id)
      .then(setMembers)
      .catch((e) => setError(e?.response?.data?.detail || e?.message || "Failed to load"))
      .finally(() => setLoading(false));
  }, [open, activeWorkspace?.id]);

  const handleRemove = async (member: WorkspaceMember) => {
    if (member.role === "owner" || !activeWorkspace || !isOwner) return;
    setRemoving(member.user_id);
    setError(null);
    try {
      await removeWorkspaceMember(activeWorkspace.id, member.user_id);
      setMembers((prev) => prev.filter((m) => m.user_id !== member.user_id));
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "Failed to remove");
    } finally {
      setRemoving(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Users className="mr-2 h-4 w-4" />
          Collaborators
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Collaborators — {activeWorkspace?.name ?? "Workspace"}
          </DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-2">
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            {members.length === 0 && !loading && (
              <p className="text-sm text-muted-foreground">
                No collaborators yet. Use Invite to add people.
              </p>
            )}
            {members.map((member) => (
              <div
                key={member.user_id}
                className="flex items-center gap-3 rounded-lg border border-border/60 px-3 py-2"
              >
                {member.role === "collaborator" && isOwner && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 shrink-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => handleRemove(member)}
                    disabled={removing === member.user_id}
                    aria-label={`Remove ${member.name}`}
                  >
                    {removing === member.user_id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <UserMinus className="h-4 w-4" />
                    )}
                  </Button>
                )}
                {member.role === "owner" && (
                  <span className="h-8 w-8 shrink-0" aria-hidden />
                )}
                <Avatar className="h-8 w-8 shrink-0">
                  <AvatarImage src={member.picture} alt={member.name} />
                  <AvatarFallback className="text-xs">
                    {(member.name?.[0] || "?").toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {member.name || "Unknown"}
                    {member.role === "owner" && (
                      <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                        (owner)
                      </span>
                    )}
                  </p>
                  {member.email && (
                    <p className="truncate text-xs text-muted-foreground">
                      {member.email}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
