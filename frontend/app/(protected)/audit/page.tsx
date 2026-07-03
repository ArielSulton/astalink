"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type AuditSummary } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { History, ArrowRight } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  approved: "text-emerald-400 bg-emerald-500/10 border-emerald-500/15",
  rejected: "text-rose-400 bg-rose-500/10 border-rose-500/15",
  rejected_after_max_revisions: "text-rose-400 bg-rose-500/10 border-rose-500/15",
  awaiting_approval: "text-amber-400 bg-amber-500/10 border-amber-500/15",
  in_progress: "text-primary bg-primary/10 border-primary/15",
};

export default function AuditTrail() {
  const [items, setItems] = useState<AuditSummary[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    // Guard against out-of-order responses when switching workspaces fast.
    let stale = false;
    setItems([]);
    setLoading(true);
    setFetchError(null);
    const fetchData = async () => {
      try {
        const sb = createClient();
        const { data: { session } } = await sb.auth.getSession();
        if (!session || stale) return;
        const res = await api.listAudit(workspaceId, session.access_token);
        if (!stale) setItems(res.audits);
      } catch (e) {
        if (!stale) setFetchError(e instanceof Error ? e.message : "Gagal memuat");
      } finally {
        if (!stale) setLoading(false);
      }
    };
    fetchData();
    return () => { stale = true; };
  }, [workspaceId]);

  return (
    <main className="p-8 max-w-4xl mx-auto bg-background min-h-screen text-foreground">
      <div className="flex justify-between items-center mb-8 flex-wrap gap-4">
        <div>
          <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em] mb-1">
            Decision Ledger
          </p>
          <h1 className="text-foreground text-2xl font-bold tracking-tight">
            Jejak Audit
          </h1>
        </div>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>

      {!workspaceId && (
        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm">
          Pilih workspace untuk melihat jejak keputusan.
        </div>
      )}

      {workspaceId && fetchError && (
        <div className="bg-card border border-rose-500/20 rounded-2xl p-8 text-center text-rose-400 text-sm">
          Gagal memuat jejak audit: {fetchError}
        </div>
      )}

      {workspaceId && !fetchError && loading && (
        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm">
          <span className="inline-block w-2 h-2 rounded-full bg-primary animate-ping mr-2.5" />
          Memuat…
        </div>
      )}

      {workspaceId && !fetchError && !loading && items.length === 0 && (
        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm">
          Belum ada keputusan tercatat untuk workspace ini.
        </div>
      )}

      {workspaceId && items.length > 0 && (
        <ul className="space-y-3">
          {items.map((it) => {
            const formattedDate = new Date(it.created_at).toLocaleDateString("id-ID", {
              day: "numeric", month: "short", year: "numeric",
              hour: "2-digit", minute: "2-digit",
            });
            const badge = STATUS_STYLE[it.status] ?? "text-muted-foreground bg-secondary border-border";
            return (
              <li
                key={it.audit_id}
                className="flex items-center justify-between p-4 bg-card border border-border rounded-2xl hover:border-primary/30 hover:bg-primary/[0.04] transition-all duration-200"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                    <History className="h-5 w-5 text-primary" />
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
                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider border ${badge}`}>
                    {it.status}
                  </span>
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
