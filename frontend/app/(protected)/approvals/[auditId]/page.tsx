"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, type ApprovalDetail } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { PinModal } from "@/components/pin-modal";
import { AllocationChart } from "@/components/allocation-chart";
import { ShieldCheck, Scale } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";

export default function ApprovalDetailPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<ApprovalDetail | null>(null);
  const [pinOpen, setPinOpen] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      setDetail(await api.getApproval(auditId, session.access_token));
    };
    load();
  }, [auditId]);

  const submitPin = async (pin: string) => {
    setPinError(null);
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return;
    try {
      await api.approve(auditId, pin, session.access_token);
      router.push(`/audit/${auditId}`);
    } catch (err) {
      setPinError(err instanceof Error ? err.message : "Gagal");
    }
  };

  const reject = async () => {
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return;
    await api.reject(auditId, "User rejected", session.access_token);
    router.push("/approvals");
  };

  if (!detail) {
    return (
      <div className="h-screen flex items-center justify-center bg-background text-muted-foreground text-xs font-mono tracking-wider">
        <span className="w-2 h-2 rounded-full bg-chart-2 animate-ping mr-2.5" />
        Memuat detail approval…
      </div>
    );
  }

  const plan = detail.plan_json;
  const isRejected = detail.legal_status === "rejected" || detail.legal_status === "rejected_after_max_revisions";

  return (
    <main className="p-8 max-w-4xl mx-auto bg-background min-h-screen text-foreground space-y-5">
      <PageHeader eyebrow="Review Request" title={`Approval #${auditId.slice(0, 8)}…`} />

      {/* ── Proposed Allocation ── */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck className="h-5 w-5 text-chart-2" />
          <h2 className="text-foreground font-bold text-base tracking-tight">Alokasi yang diusulkan</h2>
        </div>
        {plan ? <AllocationChart weights={plan.weights} /> : <p className="text-sm text-muted-foreground">Tidak ada data alokasi.</p>}
        {plan?.narration && (
          <p className="mt-4 text-sm text-muted-foreground leading-relaxed bg-secondary border border-border rounded-xl p-4">
            {plan.narration}
          </p>
        )}
      </section>

      {/* ── Regulatory Compliance ── */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3 border-b border-border pb-4">
          <div className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-chart-2" />
            <h2 className="text-foreground font-bold text-base tracking-tight">Kepatuhan regulasi</h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground font-medium">Status:</span>
            <StatusBadge status={detail.legal_status} />
          </div>
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
                  {c.pasal && (
                    <span className="text-[10px] text-foreground font-semibold font-mono">
                      Pasal {c.pasal}{c.ayat ? ` ayat (${c.ayat})` : ""}
                    </span>
                  )}
                </div>
                <div className="italic font-serif pl-3 border-l border-border mt-2 text-foreground/85">
                  &ldquo;{c.span}&rdquo;
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ── Actions ── */}
      <div className="flex gap-4">
        <button
          onClick={reject}
          className="flex-1 py-3 rounded-xl border border-border bg-secondary text-foreground text-sm font-semibold hover:bg-secondary/80 hover:border-border/60 transition-all duration-200"
        >
          Reject
        </button>
        <button
          onClick={() => setPinOpen(true)}
          className="flex-1 py-3 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-semibold disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed disabled:shadow-none transition-all duration-200"
          disabled={isRejected}
        >
          Approve dengan PIN
        </button>
      </div>

      <PinModal
        open={pinOpen}
        onSubmit={submitPin}
        onClose={() => setPinOpen(false)}
        error={pinError}
      />
    </main>
  );
}
