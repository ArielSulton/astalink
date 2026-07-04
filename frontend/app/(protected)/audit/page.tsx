"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type AuditSummary } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { History, ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";

export default function AuditTrail() {
  const [items, setItems] = useState<AuditSummary[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    const fetchData = async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      const res = await api.listAudit(workspaceId, session.access_token);
      setItems(res.audits);
    };
    fetchData();
  }, [workspaceId]);

  return (
    <main className="p-8 max-w-4xl mx-auto bg-background min-h-screen text-foreground">
      <PageHeader eyebrow="Decision Ledger" title="Jejak Audit" className="mb-8">
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </PageHeader>

      {!workspaceId && (
        <EmptyState icon={History} title="Pilih Workspace">
          Pilih workspace untuk melihat jejak keputusan.
        </EmptyState>
      )}

      {workspaceId && items.length === 0 && (
        <EmptyState icon={History} title="Belum Ada Keputusan">
          Belum ada keputusan tercatat untuk workspace ini.
        </EmptyState>
      )}

      {workspaceId && items.length > 0 && (
        <ul className="space-y-3">
          {items.map((it) => {
            const formattedDate = new Date(it.created_at).toLocaleDateString("id-ID", {
              day: "numeric", month: "short", year: "numeric",
              hour: "2-digit", minute: "2-digit",
            });
            return (
              <li
                key={it.audit_id}
                className="flex items-center justify-between p-4 bg-card border border-border rounded-2xl hover:border-chart-2/30 hover:bg-chart-2/[0.04] transition-all duration-200"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-chart-2/10 border border-chart-2/20 flex items-center justify-center shrink-0">
                    <History className="h-5 w-5 text-chart-2" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-bold text-foreground text-sm tracking-tight truncate">
                      {it.intent ?? "Keputusan Portofolio"}
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono mt-0.5">
                      {formattedDate}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <StatusBadge status={it.status} />
                  <Link
                    href={`/audit/${it.audit_id}`}
                    className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold transition-all duration-200"
                  >
                    Detail
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}
