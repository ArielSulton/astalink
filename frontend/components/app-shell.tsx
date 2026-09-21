"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppSidebar } from "@/components/app-sidebar";
import { MobileNavigation } from "@/components/mobile-navigation";
import { NavUser } from "@/components/nav-user";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { useWorkspace } from "@/components/workspace-context";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { api } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

type ApprovalCount = {
  workspaceId: string;
  count: number;
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const { workspaceId } = useWorkspace();
  const [approvalCount, setApprovalCount] = useState<ApprovalCount | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      const {
        data: { session },
      } = await createClient().auth.getSession();
      if (!session || cancelled) return;
      try {
        const me = await api.getMe(session.access_token);
        if (!cancelled) setIsAdmin(me.is_admin);
      } catch {
        // Fail closed: admin-only destinations stay hidden on both surfaces.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;

    const refresh = async () => {
      try {
        const {
          data: { session },
        } = await createClient().auth.getSession();
        if (!session || cancelled) return;
        const response = await api.listApprovals(
          workspaceId,
          session.access_token,
        );
        if (!cancelled) {
          setApprovalCount({
            workspaceId,
            count: response.approvals.length,
          });
        }
      } catch {
        return;
      }
    };

    void refresh();
    const timer = window.setInterval(refresh, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [workspaceId]);

  const pendingApprovals =
    approvalCount?.workspaceId === workspaceId ? approvalCount.count : 0;

  return (
    <SidebarProvider className="h-svh">
      <AppSidebar pendingApprovals={pendingApprovals} isAdmin={isAdmin} />
      <SidebarInset className="min-h-0">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border px-3 lg:hidden">
          <Link href="/dashboard" className="font-bold">
            AstaLink
          </Link>
          <div className="ml-auto flex items-center gap-1">
            <WorkspaceSwitcher variant="header" />
            <NavUser variant="header" isAdmin={isAdmin} />
          </div>
        </header>
        <div className="min-h-0 flex-1 overflow-auto pb-[calc(8rem+env(safe-area-inset-bottom))] lg:pb-0">
          {children}
        </div>
      </SidebarInset>
      <MobileNavigation pendingApprovals={pendingApprovals} />
    </SidebarProvider>
  );
}
