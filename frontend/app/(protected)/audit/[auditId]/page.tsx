"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { AuditTimeline } from "@/components/audit-timeline";

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
  completed: "bg-green-100 text-green-800",
  awaiting_approval: "bg-yellow-100 text-yellow-800",
  in_progress: "bg-blue-100 text-blue-800",
  rejected: "bg-red-100 text-red-800",
  rejected_after_max_revisions: "bg-red-100 text-red-800",
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

  if (fetchError) return <p className="p-6 text-destructive">Gagal memuat: {fetchError}</p>;
  if (!row) return <p className="p-6 text-muted-foreground">Memuat…</p>;

  return (
    <main className="p-6 max-w-2xl mx-auto space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Audit Trail</h1>
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[row.status] ?? "bg-muted"}`}
        >
          {row.status}
        </span>
      </div>
      <p className="text-xs text-muted-foreground font-mono">{auditId}</p>
      <AuditTimeline events={buildEvents(row)} />
    </main>
  );
}
