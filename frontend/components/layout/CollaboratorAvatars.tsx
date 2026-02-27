"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { usePresence } from "@/lib/ws/usePresence";
import { useWebSocket } from "@/lib/ws/WebSocketProvider";

const PAGE_LABELS: Record<string, string> = {
  "/chat": "Chat",
  "/pdf": "PDF Viewer",
  "/cross-eval": "Cross-Eval",
};

function pageLabel(path: string): string {
  return PAGE_LABELS[path] || path;
}

export function CollaboratorAvatars() {
  const presence = usePresence();
  const { connected } = useWebSocket();

  if (!connected || presence.length === 0) return null;

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex items-center -space-x-2">
        {presence.slice(0, 5).map((user) => (
          <Tooltip key={user.user_id}>
            <TooltipTrigger asChild>
              <div className="relative">
                <Avatar className="h-7 w-7 border-2 border-background">
                  <AvatarImage src={user.picture} alt={user.name} />
                  <AvatarFallback className="text-[10px]">
                    {(user.name?.[0] || "?").toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-background bg-green-500" />
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              <p className="font-medium">{user.name || "Collaborator"}</p>
              <p className="text-muted-foreground">
                on {pageLabel(user.current_page)}
              </p>
            </TooltipContent>
          </Tooltip>
        ))}
        {presence.length > 5 && (
          <div className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-background bg-muted text-[10px] font-medium">
            +{presence.length - 5}
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}
