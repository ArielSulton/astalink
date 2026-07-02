"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type ApprovalSummary } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { FileCheck2, ArrowRight } from "lucide-react";

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
    <main className="p-8 max-w-4xl mx-auto bg-background min-h-screen text-foreground">
      <div className="flex justify-between items-center mb-8 flex-wrap gap-4">
        <div>
          <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em] mb-1">
            Verification Inbox
          </p>
          <h1 className="text-foreground text-2xl font-bold tracking-tight">
            Pending Approvals
          </h1>
        </div>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>

      {!workspaceId && (
        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm">
          Pilih workspace untuk melihat daftar approval yang tertunda.
        </div>
      )}

      {workspaceId && items.length === 0 && (
        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm">
          Tidak ada approval yang tertunda untuk workspace ini.
        </div>
      )}

      {workspaceId && items.length > 0 && (
        <ul className="space-y-3">
          {items.map((it) => {
            const formattedDate = new Date(it.created_at).toLocaleDateString("id-ID", {
              day: "numeric",
              month: "short",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit"
            });
            return (
              <li
                key={it.audit_id}
                className="flex items-center justify-between p-4 bg-card border border-border rounded-2xl hover:border-primary/30 hover:bg-primary/[0.04] transition-all duration-200 group"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                    <FileCheck2 className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-bold text-foreground text-sm tracking-tight truncate">
                      {it.intent ?? "Otorisasi Portofolio Saham"}
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono mt-0.5">
                      Diajukan pada {formattedDate}
                    </div>
                  </div>
                </div>
                <Link
                  href={`/approvals/${it.audit_id}`}
                  className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold hover:shadow-[0_0_14px_rgba(37,99,235,0.3)] transition-all duration-200"
                >
                  Review
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}
