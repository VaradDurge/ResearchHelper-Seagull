"use client";

import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { GoogleAuthGate } from "@/components/auth/GoogleAuthGate";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <GoogleAuthGate>
      <SidebarProvider>
        <Sidebar />
        <SidebarInset>
          <Header />
          <main className="flex-1 p-6 overflow-hidden">{children}</main>
        </SidebarInset>
      </SidebarProvider>
    </GoogleAuthGate>
  );
}
