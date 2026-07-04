"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type AuditDetail } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { AllocationChart } from "@/components/allocation-chart";
import { Target, ShieldCheck, Scale, CheckCircle2, Receipt, ArrowLeft } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";

export default function AuditDetailPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [detail, setDetail] = useState<AuditDetail | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    let stale = false;
    setDetail(null);
    setFetchError(null);
    const load = async () => {
      try {
        const sb = createClient();
        const { data: { session } } = await sb.auth.getSession();
        if (!session || stale) return;
        const res = await api.getAudit(auditId, session.access_token);
        if (!stale) setDetail(res);
      } catch (e) {
        // Stale deep links (deleted run, another user's audit_id) land here as 404.
        if (!stale) setFetchError(e instanceof Error ? e.message : "Gagal memuat");
      }
    };
    load();
    return () => { stale = true; };
  }, [auditId]);

  if (fetchError) {
    return (
      <main className="p-8 max-w-3xl mx-auto bg-background min-h-screen text-foreground space-y-4">
        <div className="bg-card border border-rose-500/20 rounded-2xl p-8 text-center text-sm text-rose-400">
          Gagal memuat jejak audit: {fetchError.startsWith("404") ? "tidak ditemukan atau bukan milik Anda." : fetchError}
        </div>
        <Link
          href="/audit"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Kembali ke Jejak Audit
        </Link>
      </main>
    );
  }

  if (!detail) {
    return (
      <div className="h-screen flex items-center justify-center bg-background text-muted-foreground text-xs font-mono tracking-wider">
        <span className="w-2 h-2 rounded-full bg-chart-2 animate-ping mr-2.5" />
        Memuat jejak audit…
      </div>
    );
  }

  const plan = detail.allocation_plan;

  return (
    <main className="p-8 max-w-4xl mx-auto bg-background min-h-screen text-foreground space-y-5">
      <PageHeader eyebrow="Decision Trace" title={`Audit #${auditId.slice(0, 8)}…`}>
        <StatusBadge status={detail.status} />
      </PageHeader>

      {/* 1 — Intent */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-2 mb-2">
          <Target className="h-5 w-5 text-chart-2" />
          <h2 className="text-foreground font-bold text-base tracking-tight">Permintaan</h2>
        </div>
        <p className="text-sm text-muted-foreground">{detail.intent ?? "—"}</p>
      </section>

      {/* 2 — Alokasi */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck className="h-5 w-5 text-chart-2" />
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
            <Scale className="h-5 w-5 text-chart-2" />
            <h2 className="text-foreground font-bold text-base tracking-tight">Kepatuhan regulasi</h2>
          </div>
          <StatusBadge status={detail.legal_status} />
        </div>
        {detail.legal_citations.length === 0 ? (
          <p className="text-sm text-muted-foreground">Tidak ada catatan hukum terlampir.</p>
        ) : (
          <ul className="space-y-4">
            {detail.legal_citations.map((c, i) => (
              <li key={i} className="bg-secondary border border-border rounded-xl p-4 text-sm leading-relaxed text-muted-foreground">
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <span className="px-2 py-0.5 rounded bg-chart-2/10 border border-chart-2/15 font-mono text-[9px] font-bold text-chart-2 uppercase tracking-wider">
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
          <Receipt className="h-5 w-5 text-chart-2" />
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
                  <StatusBadge status={t.status} className="text-[9px]" />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
