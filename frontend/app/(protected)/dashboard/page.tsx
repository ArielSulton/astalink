"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { AllocationChart } from "@/components/allocation-chart";
import dynamic from "next/dynamic";
const PriceChart = dynamic(() => import("@/components/price-chart").then(m => ({ default: m.PriceChart })), { ssr: false, loading: () => <div className="h-64 flex items-center justify-center text-muted-foreground text-xs font-mono">Memuat chart…</div> });
import { TickerCard } from "@/components/ticker-card";
import { createClient } from "@/lib/supabase/client";
import { api, type AgentRunResponse, type TickerChartData } from "@/lib/api-client";

const DEFAULT_WATCHLIST = ["BBCA.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"];

const legalColor: Record<string, string> = {
  approved: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/15",
  partial: "bg-amber-500/10 text-amber-400 border border-amber-500/15",
  rejected: "bg-rose-500/10 text-rose-400 border border-rose-500/15",
  rejected_after_max_revisions: "bg-rose-500/10 text-rose-400 border border-rose-500/15",
};

export default function DashboardPage() {
  const router = useRouter();

  const [watchlist, setWatchlist] = useState<TickerChartData[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>(DEFAULT_WATCHLIST[0]);
  const [marketLoading, setMarketLoading] = useState(true);

  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentRunResponse | null>(null);

  useEffect(() => {
    api
      .getWatchlist(DEFAULT_WATCHLIST)
      .then((data) => setWatchlist(data))
      .catch(() => {})
      .finally(() => setMarketLoading(false));
  }, []);

  const selectedData = watchlist.find((t) => t.ticker === selectedTicker) ?? null;

  async function handleRun() {
    if (!workspaceId) { toast.error("Pilih workspace terlebih dahulu."); return; }
    if (!message.trim()) { toast.error("Masukkan perintah."); return; }
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) { router.push("/login"); return; }

    setLoading(true);
    setResult(null);
    try {
      const res = await api.runAgent(
        { message: message.trim(), workspace_id: workspaceId },
        session.access_token,
      );
      setResult(res);
      const ls = res.legal_status ?? "";
      if (["rejected", "rejected_after_max_revisions"].includes(ls)) {
        toast.error(`Ditolak secara legal: ${ls}`);
      } else if (res.user_approval === null) {
        toast.info("Menunggu approval Anda — periksa halaman Approvals atau gunakan tombol Tinjau & Setujui di bawah.");
      } else {
        toast.success("Analisis selesai — silakan tinjau alokasi di bawah.");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal menghubungi agen.");
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    if (!result) return;
    router.push(`/approvals/${result.audit_id}`);
  }

  const isRejected = ["rejected", "rejected_after_max_revisions"].includes(
    result?.legal_status ?? ""
  );

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* ── Market Watch Header ── */}
      <div className="border-b border-border px-6 py-5 bg-card/40">
        <div className="flex items-center justify-between mb-5">
          <div>
            <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em]">
              Market Watch
            </p>
            <h1 className="text-foreground text-xl font-bold leading-tight mt-0.5 tracking-tight">
              IDX Blue Chips
            </h1>
          </div>
          <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {DEFAULT_WATCHLIST.map((ticker) => {
            const data = watchlist.find((t) => t.ticker === ticker);
            return (
              <TickerCard
                key={ticker}
                ticker={ticker}
                lastClose={marketLoading ? null : (data?.last_close ?? null)}
                priceChangePct={marketLoading ? null : (data?.price_change_pct ?? null)}
                rsi14={marketLoading ? null : (data?.rsi14 ?? null)}
                selected={selectedTicker === ticker}
                onClick={() => setSelectedTicker(ticker)}
              />
            );
          })}
        </div>
      </div>

      {/* ── Chart Area ── */}
      <div className="px-6 py-5 border-b border-border">
        {marketLoading ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground text-xs font-mono tracking-wider">
            <span className="w-2 h-2 rounded-full bg-primary animate-ping mr-2.5" />
            Memuat data pasar…
          </div>
        ) : selectedData && selectedData.price_series.length > 0 ? (
          <PriceChart
            ticker={selectedData.ticker}
            data={selectedData.price_series}
            lastClose={selectedData.last_close}
            priceChangePct={selectedData.price_change_pct}
            bbUpper={selectedData.bb_upper}
            bbLower={selectedData.bb_lower}
          />
        ) : (
          <div className="h-64 flex items-center justify-center text-muted-foreground text-xs font-mono">
            Data tidak tersedia untuk {selectedTicker}
          </div>
        )}
      </div>

      {/* ── AI Agent Section ── */}
      <div className="px-6 py-6 flex-1 max-w-4xl w-full mx-auto space-y-4">
        <div className="bg-card border border-border rounded-2xl p-6 shadow-xl">
          <h2 className="text-foreground font-bold text-base mb-1 tracking-tight">Perintah AI</h2>
          <p className="text-muted-foreground text-xs mb-4">
            Deskripsikan tujuan investasi Anda. AI akan menganalisis pasar, bisnis, risiko, dan legalitas secara otomatis.
          </p>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Contoh: Analisis dan optimalkan portofolio saya dengan fokus BBCA dan TLKM, toleransi risiko sedang."
            className="w-full rounded-xl border border-border bg-secondary px-4 py-3 text-foreground text-sm resize-none focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all duration-200 placeholder:text-muted-foreground/50"
            rows={3}
          />
          <div className="flex justify-end mt-4">
            <button
              onClick={handleRun}
              disabled={loading || !message.trim()}
              className="px-6 py-2.5 rounded-full bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 hover:shadow-[0_0_16px_rgba(37,99,235,0.35)] disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed disabled:shadow-none transition-all duration-200"
            >
              {loading ? "Menganalisis…" : "Jalankan"}
            </button>
          </div>
        </div>

        {/* ── Agent Result ── */}
        {result && (
          <div className="bg-card border border-border rounded-2xl p-6 space-y-5 shadow-xl animate-fade-in">
            <div className="flex items-center gap-3 flex-wrap">
              {result.intent && (
                <Badge variant="outline" className="font-mono text-xs text-muted-foreground bg-secondary border-border">
                  {result.intent}
                </Badge>
              )}
              {result.legal_status && (
                <span
                  className={`rounded-full px-3 py-0.5 text-[10px] font-bold font-mono uppercase tracking-wider ${
                    legalColor[result.legal_status] ?? "bg-secondary text-muted-foreground"
                  }`}
                >
                  {result.legal_status}
                </span>
              )}
            </div>

            {result.allocation_plan && (
              <>
                <Separator className="bg-border" />
                <div className="space-y-4">
                  <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">Alokasi Portofolio</p>
                  <AllocationChart weights={result.allocation_plan.weights} />
                  {result.allocation_plan.narration && (
                    <p className="text-sm text-muted-foreground mt-4 leading-relaxed bg-secondary border border-border rounded-xl p-4">
                      {result.allocation_plan.narration}
                    </p>
                  )}
                </div>
              </>
            )}

            {result.errors.length > 0 && (
              <>
                <Separator className="bg-border" />
                <div className="space-y-2">
                  <p className="text-xs font-bold text-rose-400 uppercase tracking-wider font-mono">Error Log</p>
                  <div className="space-y-1 bg-rose-500/5 border border-rose-500/10 rounded-xl p-4">
                    {result.errors.map((e, i) => (
                      <p key={i} className="text-xs text-rose-400 font-mono">
                        [{e.node}] {e.reason}
                      </p>
                    ))}
                  </div>
                </div>
              </>
            )}

            {!isRejected && result.user_approval === null && (
              <>
                <Separator className="bg-border" />
                <div className="flex justify-end">
                  <button
                    onClick={handleApprove}
                    className="px-6 py-2.5 rounded-full bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 hover:shadow-[0_0_16px_rgba(37,99,235,0.35)] transition-all duration-200"
                  >
                    Tinjau & Setujui
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
