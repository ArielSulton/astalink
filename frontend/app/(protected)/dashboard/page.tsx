"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { AllocationChart } from "@/components/allocation-chart";
import { PriceChart } from "@/components/price-chart";
import { TickerCard } from "@/components/ticker-card";
import { createClient } from "@/lib/supabase/client";
import { api, type AgentRunResponse, type TickerChartData } from "@/lib/api-client";

const DEFAULT_WATCHLIST = ["BBCA.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"];

const legalColor: Record<string, string> = {
  approved: "bg-green-100 text-green-800",
  partial: "bg-yellow-100 text-yellow-800",
  rejected: "bg-red-100 text-red-800",
  rejected_after_max_revisions: "bg-red-100 text-red-800",
};

export default function DashboardPage() {
  const router = useRouter();

  // Market state
  const [watchlist, setWatchlist] = useState<TickerChartData[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>(DEFAULT_WATCHLIST[0]);
  const [marketLoading, setMarketLoading] = useState(true);

  // Agent state
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentRunResponse | null>(null);

  // Fetch watchlist on mount — public endpoint, no token needed
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
    <div className="min-h-screen bg-[#0a0b0d] flex flex-col">
      {/* ── Market Watch Header ── */}
      <div className="border-b border-[#1e2028] px-6 py-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-[#a8acb3] text-[10px] font-mono uppercase tracking-widest">
              Market Watch
            </p>
            <h1 className="text-white text-lg font-semibold leading-tight mt-0.5">
              IDX Blue Chips
            </h1>
          </div>
          <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
        </div>

        {/* Ticker grid */}
        <div className="grid grid-cols-4 gap-3">
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
      <div className="px-6 py-5 border-b border-[#1e2028]">
        {marketLoading ? (
          <div className="h-64 flex items-center justify-center text-[#a8acb3] text-sm font-mono">
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
          <div className="h-64 flex items-center justify-center text-[#a8acb3] text-sm font-mono">
            Data tidak tersedia untuk {selectedTicker}
          </div>
        )}
      </div>

      {/* ── AI Agent Section ── */}
      <div className="px-6 py-6 flex-1">
        <div className="bg-white rounded-2xl p-6">
          <h2 className="text-[#0a0b0d] font-semibold text-base mb-1">Perintah AI</h2>
          <p className="text-[#5b616e] text-sm mb-4">
            Deskripsikan tujuan investasi Anda. AI akan menganalisis pasar, bisnis, risiko, dan legalitas.
          </p>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Contoh: Analisis dan optimalkan portofolio saya dengan fokus BBCA dan TLKM, toleransi risiko sedang."
            className="w-full rounded-xl border border-[#dee1e6] px-4 py-3 text-[#0a0b0d] text-sm resize-none focus:outline-none focus:border-[#0052ff] focus:ring-1 focus:ring-[#0052ff] transition-colors"
            rows={3}
          />
          <div className="flex justify-end mt-3">
            <button
              onClick={handleRun}
              disabled={loading || !message.trim()}
              className="px-6 py-2.5 rounded-full bg-[#0052ff] text-white text-sm font-semibold hover:bg-[#003ecc] disabled:bg-[#a8b8cc] disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Menganalisis…" : "Jalankan"}
            </button>
          </div>
        </div>

        {/* ── Agent Result ── */}
        {result && (
          <div className="mt-4 bg-white rounded-2xl p-6 space-y-4">
            {/* Header row */}
            <div className="flex items-center gap-3 flex-wrap">
              {result.intent && (
                <Badge variant="outline" className="font-mono text-xs">
                  {result.intent}
                </Badge>
              )}
              {result.legal_status && (
                <span
                  className={`rounded-full px-3 py-0.5 text-xs font-semibold ${
                    legalColor[result.legal_status] ?? "bg-gray-100 text-gray-800"
                  }`}
                >
                  {result.legal_status}
                </span>
              )}
            </div>

            {/* Allocation chart */}
            {result.allocation_plan && (
              <>
                <Separator />
                <div>
                  <p className="text-xs font-medium text-[#5b616e] mb-3">Alokasi Portofolio</p>
                  <AllocationChart weights={result.allocation_plan.weights} />
                  {result.allocation_plan.narration && (
                    <p className="text-sm text-[#5b616e] mt-3 leading-relaxed">
                      {result.allocation_plan.narration}
                    </p>
                  )}
                </div>
              </>
            )}

            {/* Errors */}
            {result.errors.length > 0 && (
              <>
                <Separator />
                <div className="space-y-1">
                  {result.errors.map((e, i) => (
                    <p key={i} className="text-xs text-red-600 font-mono">
                      [{e.node}] {e.reason}
                    </p>
                  ))}
                </div>
              </>
            )}

            {/* Approve button */}
            {!isRejected && result.user_approval === null && (
              <>
                <Separator />
                <div className="flex justify-end">
                  <button
                    onClick={handleApprove}
                    className="px-6 py-2.5 rounded-full bg-[#0052ff] text-white text-sm font-semibold hover:bg-[#003ecc] transition-colors"
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
