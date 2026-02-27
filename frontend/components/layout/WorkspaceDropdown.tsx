"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ChevronDown, Plus, MoreHorizontal, Users } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useWorkspace } from "@/store/workspaceStore";

const MAX_WORKSPACES = 5;

export function WorkspaceDropdown() {
  const {
    workspaces,
    activeWorkspace,
    switchWorkspace,
    createWorkspace,
    renameWorkspace,
  } = useWorkspace();
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [workspaceToRename, setWorkspaceToRename] = useState<string | null>(null);
  const [renameName, setRenameName] = useState("");
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSwitch = async (id: string) => {
    if (id === activeWorkspace?.id) return;
    try {
      await switchWorkspace(id);
      window.location.reload();
    } catch {
      // ignore
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    setError(null);
    try {
      const ws = await createWorkspace(name);
      setCreateDialogOpen(false);
      setNewName("");
      await switchWorkspace(ws.id);
      window.location.reload();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Failed to create workspace");
    } finally {
      setCreating(false);
    }
  };

  const openRenameDialog = (workspaceId: string, currentName: string) => {
    setWorkspaceToRename(workspaceId);
    setRenameName(currentName);
    setError(null);
    setRenameDialogOpen(true);
  };

  const handleRename = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceToRename) return;
    const name = renameName.trim();
    if (!name) return;
    setRenaming(true);
    setError(null);
    try {
      await renameWorkspace(workspaceToRename, name);
      setRenameDialogOpen(false);
      setWorkspaceToRename(null);
      setRenameName("");
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Failed to rename workspace");
    } finally {
      setRenaming(false);
    }
  };

  const canCreate = workspaces.length < MAX_WORKSPACES;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="w-full justify-between">
            <span className="flex items-center gap-2 truncate">
              {activeWorkspace?.is_shared && (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-500 dark:text-emerald-400">
                  <Users className="h-3 w-3" />
                  Shared
                </span>
              )}
              <span className="truncate">{activeWorkspace?.name ?? "Loading..."}</span>
            </span>
            <ChevronDown className="h-4 w-4 shrink-0" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          {workspaces.map((ws) => {
            const isActive = ws.id === activeWorkspace?.id;
            return (
              <DropdownMenuItem
                key={ws.id}
                onClick={() => handleSwitch(ws.id)}
                className={`rounded-md border px-2 py-1.5 flex items-center gap-2 ${
                  isActive
                    ? "bg-accent border-border text-accent-foreground"
                    : "border-transparent"
                }`}
              >
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 shrink-0"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    openRenameDialog(ws.id, ws.name);
                  }}
                  aria-label={`Rename ${ws.name}`}
                >
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
                <span className="truncate flex-1">{ws.name}</span>
                {ws.is_shared && (
                  <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-medium text-emerald-500 dark:text-emerald-400">
                    <Users className="h-2.5 w-2.5" />
                    Shared
                  </span>
                )}
              </DropdownMenuItem>
            );
          })}
          {canCreate && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setCreateDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create New Workspace
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Create Workspace</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Workspace name"
              maxLength={100}
              autoFocus
            />
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setCreateDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={!newName.trim() || creating}>
                {creating ? "Creating..." : "Create"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Rename Workspace</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleRename} className="space-y-4">
            <Input
              value={renameName}
              onChange={(e) => setRenameName(e.target.value)}
              placeholder="Workspace name"
              maxLength={100}
              autoFocus
            />
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setRenameDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={!renameName.trim() || renaming}>
                {renaming ? "Saving..." : "Save"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
