"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { AuditTimeline } from "@/components/audit-timeline";

interface AuditRow {
  audit_id: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  payload: Record<string, unknown>;
}

export default function AuditPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [row, setRow] = useState<AuditRow | null>(null);

  useEffect(() => {
    const sb = createClient();
    sb.from("audit_log").select("*").eq("audit_id", auditId).single()
      .then(({ data }) => setRow(data as AuditRow | null));
  }, [auditId]);

  if (!row) return <p className="p-6">Loading…</p>;

  const events = [
    { ts: row.created_at, node: "n1_intent", status: "intent classified" },
    ...(row.payload && (row.payload as { legal?: unknown }).legal
      ? [{ ts: row.created_at, node: "n3_legal", status: "legal decision recorded" }]
      : []),
    ...(row.completed_at
      ? [{ ts: row.completed_at, node: "completed", status: row.status }]
      : []),
  ];

  return (
    <main className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Audit Trail</h1>
      <p className="text-xs text-muted-foreground mb-4">audit_id: {auditId}</p>
      <AuditTimeline events={events} />
    </main>
  );
}
