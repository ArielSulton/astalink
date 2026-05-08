"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type ApprovalSummary } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";

export default function ApprovalsInbox() {
  const [items, setItems] = useState<ApprovalSummary[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    const fetchData = async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      const res = await api.listApprovals(workspaceId, session.access_token);
      setItems(res.approvals);
    };
    fetchData();
    const t = setInterval(fetchData, 5_000);
    return () => clearInterval(t);
  }, [workspaceId]);

  return (
    <main className="p-6 max-w-3xl mx-auto">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold">Pending Approvals</h1>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>
      {!workspaceId && <p className="text-muted-foreground">Pilih workspace untuk melihat approval.</p>}
      {workspaceId && items.length === 0 && (
        <p className="text-muted-foreground">Tidak ada approval yang tertunda.</p>
      )}
      <ul className="space-y-2">
        {items.map((it) => (
          <li key={it.audit_id} className="border rounded p-3 flex justify-between">
            <div>
              <div className="font-medium">{it.intent ?? "—"}</div>
              <div className="text-xs text-muted-foreground">{it.created_at}</div>
            </div>
            <Link className="text-blue-600 underline" href={`/approvals/${it.audit_id}`}>
              Review
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
