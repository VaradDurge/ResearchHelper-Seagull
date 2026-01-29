"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { MessageSquare, Trash2 } from "lucide-react";
import { Sidebar as ShadcnSidebar, SidebarContent, SidebarHeader } from "@/components/ui/sidebar";
import { WorkspaceDropdown } from "./WorkspaceDropdown";
import { NavigationItem } from "./NavigationItem";
import { navItems } from "@/lib/constants/nav-items";
import { getConversations, deleteConversation, Conversation } from "@/lib/api/conversations";
import { Button } from "@/components/ui/button";

export function Sidebar() {
  const [conversations, setConversations] = useState<Conversation[]>([]);

  const loadConversations = async () => {
    try {
      const data = await getConversations();
      setConversations(data.conversations.slice(0, 10));
    } catch {
      // Not logged in or error
    }
  };

  useEffect(() => {
    loadConversations();
    // Refresh every 30s
    const interval = setInterval(loadConversations, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch {
      // ignore
    }
  };

  return (
    <ShadcnSidebar>
      <SidebarHeader className="border-b p-4">
        <div className="flex items-center gap-2 mb-4">
          <h1 className="text-xl font-bold">Seagull</h1>
        </div>
        <WorkspaceDropdown />
      </SidebarHeader>
      <SidebarContent className="p-4 flex flex-col gap-4">
        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavigationItem key={item.href} item={item} />
          ))}
        </nav>

        {conversations.length > 0 && (
          <div className="mt-4">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
              Recent Chats
            </h3>
            <div className="space-y-1">
              {conversations.map((conv) => (
                <Link
                  key={conv.id}
                  href={`/chat?conversation=${conv.id}`}
                  className="flex items-center gap-2 px-2 py-1.5 text-sm rounded-md hover:bg-accent group"
                >
                  <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate flex-1">{conv.title}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100"
                    onClick={(e) => handleDelete(conv.id, e)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </Link>
              ))}
            </div>
          </div>
        )}
      </SidebarContent>
    </ShadcnSidebar>
  );
}
