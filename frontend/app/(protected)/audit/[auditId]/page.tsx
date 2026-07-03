"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type AuditDetail } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { AllocationChart } from "@/components/allocation-chart";
import { Target, ShieldCheck, Scale, CheckCircle2, Receipt } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  approved: "text-emerald-400 bg-emerald-500/10 border-emerald-500/15",
  partial: "text-amber-400 bg-amber-500/10 border-amber-500/15",
  rejected: "text-rose-400 bg-rose-500/10 border-rose-500/15",
  rejected_after_max_revisions: "text-rose-400 bg-rose-500/10 border-rose-500/15",
  awaiting_approval: "text-amber-400 bg-amber-500/10 border-amber-500/15",
};

function badge(status: string | null): string {
  if (!status) return "text-muted-foreground bg-secondary border-border";
  return STATUS_STYLE[status] ?? "text-muted-foreground bg-secondary border-border";
}

export default function AuditDetailPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [detail, setDetail] = useState<AuditDetail | null>(null);

  useEffect(() => {
    const load = async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      setDetail(await api.getAudit(auditId, session.access_token));
    };
    load();
  }, [auditId]);

  if (!detail) {
    return (
      <div className="h-screen flex items-center justify-center bg-background text-muted-foreground text-xs font-mono tracking-wider">
        <span className="w-2 h-2 rounded-full bg-primary animate-ping mr-2.5" />
        Memuat jejak audit…
      </div>
    );
  }

  const plan = detail.allocation_plan;

  return (
    <main className="p-8 max-w-4xl mx-auto bg-background min-h-screen text-foreground space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em] mb-1">
            Decision Trace
          </p>
          <h1 className="text-foreground text-2xl font-bold tracking-tight">
            Audit #{auditId.slice(0, 8)}…
          </h1>
        </div>
        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider border ${badge(detail.status)}`}>
          {detail.status}
        </span>
      </div>

      {/* 1 — Intent */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-2 mb-2">
          <Target className="h-5 w-5 text-primary" />
          <h2 className="text-foreground font-bold text-base tracking-tight">Permintaan</h2>
        </div>
        <p className="text-sm text-muted-foreground">{detail.intent ?? "—"}</p>
      </section>

      {/* 2 — Alokasi */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <h2 className="text-foreground font-bold text-base tracking-tight">Alokasi</h2>
        </div>
        {plan ? <AllocationChart weights={plan.weights} /> : <p className="text-sm text-muted-foreground">Tidak ada data alokasi.</p>}
        {plan?.narration && (
          <p className="mt-4 text-sm text-muted-foreground leading-relaxed bg-secondary border border-border rounded-xl p-4">
            {plan.narration}
          </p>
        )}
      </section>

      {/* 3 — Legal */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3 border-b border-border pb-4">
          <div className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-primary" />
            <h2 className="text-foreground font-bold text-base tracking-tight">Kepatuhan regulasi</h2>
          </div>
          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider border ${badge(detail.legal_status)}`}>
            {detail.legal_status ?? "—"}
          </span>
        </div>
        {detail.legal_citations.length === 0 ? (
          <p className="text-sm text-muted-foreground">Tidak ada catatan hukum terlampir.</p>
        ) : (
          <ul className="space-y-4">
            {detail.legal_citations.map((c, i) => (
              <li key={i} className="bg-secondary border border-border rounded-xl p-4 text-sm leading-relaxed text-muted-foreground">
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <span className="px-2 py-0.5 rounded bg-primary/10 border border-primary/15 font-mono text-[9px] font-bold text-primary uppercase tracking-wider">
                    {c.source}
                  </span>
                  <span className="text-[10px] text-foreground font-semibold font-mono">
                    Pasal {c.pasal}{c.ayat ? ` ayat (${c.ayat})` : ""}
                  </span>
                </div>
                <div className="italic font-serif pl-3 border-l border-border mt-2 text-foreground/85">
                  &ldquo;{c.span}&rdquo;
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* 4 — Transaksi */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-2 mb-4">
          <Receipt className="h-5 w-5 text-primary" />
          <h2 className="text-foreground font-bold text-base tracking-tight">Transaksi</h2>
        </div>
        {detail.transactions.length === 0 ? (
          <p className="text-sm text-muted-foreground flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            Tidak ada transaksi tereksekusi.
          </p>
        ) : (
          <ul className="space-y-2">
            {detail.transactions.map((t, i) => (
              <li key={i} className="flex items-center justify-between bg-secondary border border-border rounded-xl p-3 text-sm">
                <div className="flex items-center gap-2 font-mono">
                  <span className="font-bold text-foreground">{t.ticker}</span>
                  <span className="uppercase text-[10px] text-muted-foreground">{t.side}</span>
                  <span className="text-muted-foreground">×{t.quantity}</span>
                </div>
                <div className="flex items-center gap-2">
                  {t.broker_ref && <span className="text-[10px] text-muted-foreground font-mono">{t.broker_ref}</span>}
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold font-mono uppercase border ${badge(t.status)}`}>
                    {t.status}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
