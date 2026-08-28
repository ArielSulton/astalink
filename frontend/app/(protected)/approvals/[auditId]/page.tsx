"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, type ApprovalDetail } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { PinModal } from "@/components/pin-modal";
import { AllocationBuyModal } from "@/components/allocation-buy-modal";
import { AllocationChart } from "@/components/allocation-chart";
import { ShieldCheck, Scale, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";

export default function ApprovalDetailPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<ApprovalDetail | null>(null);
  const [pinOpen, setPinOpen] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  // A WhatsApp user landing here from the "Review & approve" link had no way
  // to actually execute the recommendation without separately finding the
  // chat/portfolio page again — this reuses the same buy flow directly here.
  const [buyOpen, setBuyOpen] = useState(false);
  const [allocated, setAllocated] = useState(false);

  useEffect(() => {
    let stale = false;
    setDetail(null);
    setFetchError(null);
    const load = async () => {
      try {
        const sb = createClient();
        const { data: { session } } = await sb.auth.getSession();
        if (!session || stale) return;
        const res = await api.getApproval(auditId, session.access_token);
        if (!stale) setDetail(res);
      } catch (err) {
        if (!stale) setFetchError(err instanceof Error ? err.message : "Gagal memuat");
      }
    };
    load();
    return () => { stale = true; };
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
    try {
      await api.reject(auditId, "Ditolak oleh pengguna", session.access_token);
      router.push("/approvals");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal menolak");
    }
  };

  if (fetchError) {
    return (
      <main className="p-8 max-w-3xl mx-auto bg-background min-h-screen text-foreground space-y-4">
        <div className="bg-card rounded-xl ring-1 ring-destructive/20 p-8 text-center text-sm text-destructive">
          Gagal memuat detail approval: {fetchError.includes("404") ? "Data approval tidak ditemukan atau sudah kadaluarsa." : fetchError}
        </div>
        <Link
          href="/approvals"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Kembali ke Daftar Approval
        </Link>
      </main>
    );
  }

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
  const rankedWeights = [...(plan?.weights ?? [])]
    .filter((w) => w.weight > 0)
    .sort((a, b) => b.weight - a.weight);
  const suggestedTickers = rankedWeights.length ? rankedWeights.map((w) => w.ticker) : ["BBCA"];
  const suggestedAmount = rankedWeights.length && plan
    ? plan.cash * rankedWeights[0].weight
    : null;

  return (
    <main className="p-8 max-w-4xl mx-auto bg-background min-h-screen text-foreground space-y-5">
      <PageHeader eyebrow="Tinjau Permintaan" title={`Persetujuan #${auditId.slice(0, 8)}…`} />

      {/* ── Proposed Allocation ── */}
      <section className="bg-card rounded-xl p-6 ring-1 ring-foreground/10">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck className="h-5 w-5 text-chart-2" />
          <h2 className="text-foreground font-bold text-base tracking-tight">Alokasi yang diusulkan</h2>
        </div>
        {plan ? <AllocationChart weights={plan.weights} cash={plan.cash} totalFunds={plan.total_funds} /> : <p className="text-sm text-muted-foreground">Tidak ada data alokasi.</p>}
        {plan?.narration && (
          <p className="mt-4 text-sm text-muted-foreground leading-relaxed bg-secondary border border-border rounded-xl p-4">
            {plan.narration}
          </p>
        )}
      </section>

      {/* ── Regulatory Compliance ── */}
      <section className="bg-card rounded-xl p-6 ring-1 ring-foreground/10 space-y-4">
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
      {allocated ? (
        <div className="flex items-start gap-2 rounded-xl border border-chart-2/25 bg-chart-2/[0.06] px-3.5 py-3 text-sm text-chart-2">
          Dana dari rekomendasi ini sudah dialokasikan — transaksi tercatat dan posisi
          diperbarui.{" "}
          <Link href="/portfolio" className="underline underline-offset-2 hover:text-chart-2">
            Lihat portofolio
          </Link>
        </div>
      ) : isRejected ? (
        <div className="flex items-start gap-2 rounded-xl border border-destructive/25 bg-destructive/[0.06] px-3.5 py-3 text-sm text-destructive">
          Rekomendasi ini ditolak oleh pemeriksaan kepatuhan dan tidak bisa dieksekusi dalam
          bentuk ini — lihat sitasi hukum di atas untuk alasannya.{" "}
          <Link href="/chatbot" className="underline underline-offset-2 hover:text-destructive">
            Minta analisis baru di chat
          </Link>{" "}
          dengan target atau batasan yang disesuaikan.
        </div>
      ) : (
        <p className="text-xs text-muted-foreground leading-relaxed bg-secondary border border-border rounded-xl p-3">
          AstaLink beroperasi dalam mode advisory: &ldquo;Setujui Analisis (PIN)&rdquo; hanya
          mencatat bahwa Anda meninjau dan setuju dengan rekomendasi ini —{" "}
          <strong>tidak mengeksekusi apa pun</strong>. Untuk benar-benar mengalokasikan dana,
          gunakan &ldquo;Setujui &amp; Alokasikan Dana&rdquo; di bawah.
        </p>
      )}
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={reject}
          disabled={isRejected || allocated}
          className="flex-1 py-3 rounded-xl border border-border bg-secondary text-foreground text-sm font-semibold hover:bg-secondary/80 hover:border-border/60 disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200"
        >
          Tolak
        </button>
        <button
          onClick={() => setPinOpen(true)}
          className="flex-1 py-3 rounded-xl border border-border bg-secondary text-foreground text-sm font-semibold hover:bg-secondary/80 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all duration-200"
          disabled={isRejected || allocated}
        >
          Setujui Analisis (PIN)
        </button>
        {!allocated && plan && rankedWeights.length > 0 && (
          <button
            onClick={() => setBuyOpen(true)}
            disabled={isRejected}
            className="flex-1 py-3 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-semibold disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all duration-200"
          >
            Setujui &amp; Alokasikan Dana
          </button>
        )}
      </div>

      <PinModal
        open={pinOpen}
        onSubmit={submitPin}
        onClose={() => setPinOpen(false)}
        error={pinError}
      />

      {buyOpen && (
        <AllocationBuyModal
          workspaceId={detail.workspace_id}
          suggestedTickers={suggestedTickers}
          suggestedAmount={suggestedAmount}
          onClose={() => setBuyOpen(false)}
          onSuccess={() => {
            setBuyOpen(false);
            setAllocated(true);
            toast.success("Alokasi berhasil! Saldo kas berkurang.");
          }}
        />
      )}
    </main>
  );
}
