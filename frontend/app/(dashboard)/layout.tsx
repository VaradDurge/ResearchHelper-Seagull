"use client";

import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { GoogleAuthGate } from "@/components/auth/GoogleAuthGate";
import { WorkspaceProvider, useWorkspace } from "@/store/workspaceStore";
import { WebSocketProvider } from "@/lib/ws/WebSocketProvider";
import { InvitationNotification } from "@/components/layout/InvitationNotification";

function DashboardInner({ children }: { children: React.ReactNode }) {
  const { activeWorkspace } = useWorkspace();

  return (
    <WebSocketProvider workspaceId={activeWorkspace?.id ?? null}>
      <SidebarProvider>
        <Sidebar />
        <SidebarInset>
          <Header />
          <main className="flex-1 p-6 overflow-hidden">{children}</main>
        </SidebarInset>
      </SidebarProvider>
      <InvitationNotification />
    </WebSocketProvider>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <GoogleAuthGate>
      <WorkspaceProvider>
        <DashboardInner>{children}</DashboardInner>
      </WorkspaceProvider>
    </GoogleAuthGate>
  );
}
