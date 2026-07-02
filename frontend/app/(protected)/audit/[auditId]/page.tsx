"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { AuditTimeline } from "@/components/audit-timeline";
import { GitBranch } from "lucide-react";

interface AuditRow {
  audit_id: string;
  status: string;
  intent: string | null;
  created_at: string;
  completed_at: string | null;
  payload: Record<string, unknown>;
}

type TimelineEvent = {
  ts: string;
  node: string;
  status: string;
  variant?: "default" | "success" | "error";
};

function buildEvents(row: AuditRow): TimelineEvent[] {
  const events: TimelineEvent[] = [
    { ts: row.created_at, node: "n1_intent", status: `Intent: ${row.intent ?? "unknown"}` },
  ];

  const p = row.payload as Record<string, unknown>;

  if (p.market) events.push({ ts: row.created_at, node: "n2a_market", status: "Analisis pasar selesai" });
  if (p.business) events.push({ ts: row.created_at, node: "n2b_business", status: "Analisis bisnis selesai" });
  if (p.risk) events.push({ ts: row.created_at, node: "n2c_risk", status: "Analisis risiko selesai" });
  if (p.optimizer) events.push({ ts: row.created_at, node: "n5_optimizer", status: "Alokasi dioptimasi" });

  if (p.legal) {
    const legal = p.legal as Record<string, unknown>;
    const legalStatus = (legal.status as string) ?? "unknown";
    events.push({
      ts: row.created_at,
      node: "n3_legal",
      status: `Legal: ${legalStatus}`,
      variant: legalStatus === "approved" ? "success" : legalStatus === "rejected" ? "error" : "default",
    });
  }

  if (row.status === "awaiting_approval") {
    events.push({ ts: row.created_at, node: "n6_hitl", status: "Menunggu approval pengguna" });
  }

  if (row.completed_at) {
    const isSuccess = row.status === "completed";
    events.push({
      ts: row.completed_at,
      node: "Selesai",
      status: row.status,
      variant: isSuccess ? "success" : row.status.includes("rejected") ? "error" : "default",
    });
  }

  return events;
}

const STATUS_COLOR: Record<string, string> = {
  completed: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/15",
  awaiting_approval: "bg-amber-500/10 text-amber-400 border border-amber-500/15",
  in_progress: "bg-primary/10 text-primary border border-primary/15",
  rejected: "bg-rose-500/10 text-rose-400 border border-rose-500/15",
  rejected_after_max_revisions: "bg-rose-500/10 text-rose-400 border border-rose-500/15",
};

export default function AuditPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [row, setRow] = useState<AuditRow | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    const sb = createClient();
    sb.from("audit_log").select("*").eq("audit_id", auditId).single()
      .then(({ data, error }) => {
        if (error) { setFetchError(error.message); return; }
        setRow(data as AuditRow | null);
      });
  }, [auditId]);

  if (fetchError) {
    return (
      <div className="p-8 max-w-3xl mx-auto text-rose-400 text-sm bg-background min-h-screen">
        Gagal memuat: {fetchError}
      </div>
    );
  }

  if (!row) {
    return (
      <div className="h-screen flex items-center justify-center bg-background text-muted-foreground text-xs font-mono tracking-wider">
        <span className="w-2 h-2 rounded-full bg-primary animate-ping mr-2.5" />
        Memuat audit trail…
      </div>
    );
  }

  return (
    <main className="p-8 max-w-3xl mx-auto bg-background min-h-screen text-foreground space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em] mb-1">
            Activity Logs
          </p>
          <h1 className="text-foreground text-2xl font-bold tracking-tight">Audit Trail</h1>
        </div>
        <span
          className={`rounded-full px-3 py-0.5 text-[10px] font-bold font-mono uppercase tracking-wider border ${
            STATUS_COLOR[row.status] ?? "bg-secondary text-muted-foreground border-border"
          }`}
        >
          {row.status}
        </span>
      </div>

      <div className="bg-secondary border border-border rounded-xl px-4 py-3 flex items-center gap-2">
        <GitBranch className="w-4 h-4 text-muted-foreground" />
        <span className="text-[10px] text-muted-foreground font-mono tracking-wider">{auditId}</span>
      </div>

      <div className="bg-card border border-border rounded-2xl p-6 shadow-xl">
        <AuditTimeline events={buildEvents(row)} />
      </div>
    </main>
  );
}
