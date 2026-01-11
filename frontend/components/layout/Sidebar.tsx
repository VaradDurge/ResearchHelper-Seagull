"use client";

import { Sidebar as ShadcnSidebar, SidebarContent, SidebarHeader } from "@/components/ui/sidebar";
import { WorkspaceDropdown } from "./WorkspaceDropdown";
import { NavigationItem } from "./NavigationItem";
import { navItems } from "@/lib/constants/nav-items";

export function Sidebar() {
  return (
    <ShadcnSidebar>
      <SidebarHeader className="border-b p-4">
        <div className="flex items-center gap-2 mb-4">
          <h1 className="text-xl font-bold">Seagull</h1>
        </div>
        <WorkspaceDropdown />
      </SidebarHeader>
      <SidebarContent className="p-4">
        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavigationItem key={item.href} item={item} />
          ))}
        </nav>
      </SidebarContent>
    </ShadcnSidebar>
  );
}
