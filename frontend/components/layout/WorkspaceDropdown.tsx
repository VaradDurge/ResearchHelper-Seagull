"use client";

import { Button } from "@/components/ui/button";
import { ChevronDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function WorkspaceDropdown() {
  // TODO: Connect to workspace store later
  const currentWorkspace = "My Workspace";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="w-full justify-between">
          <span className="truncate">{currentWorkspace}</span>
          <ChevronDown className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuItem>Create New Workspace</DropdownMenuItem>
        <DropdownMenuItem>Workspace 1</DropdownMenuItem>
        <DropdownMenuItem>Workspace 2</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
