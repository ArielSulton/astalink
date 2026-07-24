"use client";
import { useCallback, useEffect, useState } from "react";
import { PiggyBank, TrendingUp, Wallet, LineChart } from "lucide-react";
import { toast } from "sonner";
import { api, type PortfolioResponse, type HoldingView } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { useWorkspace } from "@/components/workspace-context";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { StatCard } from "@/components/ui/stat-card";

function idr(n: number | null | undefined): string {
  if (n == null) return "—";
  return "Rp " + n.toLocaleString("id-ID", { maximumFractionDigits: 0 });
}

function signed(n: number | null | undefined): string {
  if (n == null) return "—";
  const s = n.toLocaleString("id-ID", { maximumFractionDigits: 0 });
  return (n >= 0 ? "+Rp " : "-Rp ") + s.replace("-", "");
}

function pnlClass(n: number | null | undefined): string {
  if (n == null) return "text-muted-foreground";
  return n >= 0 ? "text-emerald-400" : "text-rose-400";
}

export default function PortfolioPage() {
  const { workspaceId } = useWorkspace();
  const [data, setData] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selling, setSelling] = useState<HoldingView | null>(null);

  const load = useCallback(async () => {
    if (!workspaceId) {
      setData(null);
      return;
    }
    setLoading(true);
    try {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      const res = await api.getPortfolio(workspaceId, session.access_token);
      setData(res);
    } catch {
      toast.error("Gagal memuat portofolio.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    load();
  }, [load]);

  const hasHoldings = data && data.holdings.length > 0;

  return (
    <div className="p-8 space-y-6 max-w-5xl w-full mx-auto bg-background min-h-screen text-foreground">
      <PageHeader
        eyebrow="Sandbox Portfolio"
        title="Portofolio"
        className="border-b border-border pb-5"
      />

      {!workspaceId && (
        <EmptyState icon={Wallet} title="Pilih Workspace">
          Pilih workspace di kanan atas untuk melihat portofolio Anda.
        </EmptyState>
      )}

      {workspaceId && loading && !data && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-28 rounded-2xl bg-card animate-pulse border border-border" />
            ))}
          </div>
          <div className="h-64 rounded-2xl bg-card animate-pulse border border-border" />
        </div>
      )}

      {workspaceId && data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Total Ekuitas" value={idr(data.total_equity)} icon={LineChart}
              hint="Kas + nilai pasar holdings" />
            <StatCard label="Kas" value={idr(data.cash_balance)} icon={PiggyBank}
              hint="Saldo tunai sandbox" />
            <StatCard label="Unrealized P&L" value={signed(data.total_unrealized_pnl)}
              icon={TrendingUp} hint="Selisih nilai pasar vs modal"
              className={data.total_unrealized_pnl != null && data.total_unrealized_pnl < 0
                ? "border-rose-500/20" : ""} />
            <StatCard label="Realized P&L" value={signed(data.total_realized_pnl)}
              icon={Wallet} hint="Akumulasi hasil penjualan" />
          </div>

          <div className="rounded-2xl border border-border bg-card overflow-hidden shadow-xl">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
                Kepemilikan Saham
              </h2>
              {loading && <span className="text-[10px] text-muted-foreground font-mono">memuat…</span>}
            </div>

            {!hasHoldings ? (
              <div className="p-8">
                <EmptyState icon={TrendingUp} title="Belum Ada Kepemilikan">
                  Portofolio kosong. Beli saham lewat Asisten AI di Dashboard
                  (analisis → setujui) untuk mengisi portofolio ini.
                </EmptyState>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-secondary/40 text-left text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
                      <th className="px-5 py-3">Saham</th>
                      <th className="px-4 py-3 text-right">Qty</th>
                      <th className="px-4 py-3 text-right">Avg Cost</th>
                      <th className="px-4 py-3 text-right">Harga</th>
                      <th className="px-4 py-3 text-right">Nilai Pasar</th>
                      <th className="px-4 py-3 text-right">Unrealized P&L</th>
                      <th className="px-4 py-3 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.holdings.map((h) => (
                      <tr key={h.ticker} className="border-b border-border/60 last:border-0 hover:bg-secondary/20 transition-colors">
                        <td className="px-5 py-3 font-mono font-bold">{h.ticker}</td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums">
                          {h.quantity.toLocaleString("id-ID", { maximumFractionDigits: 2 })}
                        </td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums text-muted-foreground">{idr(h.avg_cost)}</td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums">{idr(h.last_price)}</td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums">{idr(h.market_value)}</td>
                        <td className={`px-4 py-3 text-right font-mono tabular-nums ${pnlClass(h.unrealized_pnl)}`}>
                          {signed(h.unrealized_pnl)}
                          {h.unrealized_pnl_pct != null && (
                            <span className="block text-[10px] opacity-70">
                              {(h.unrealized_pnl_pct * 100).toFixed(1)}%
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => setSelling(h)}
                            className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-rose-500/30 text-rose-400 hover:bg-rose-500/10 transition-all"
                          >
                            Jual
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <p className="text-[10px] text-muted-foreground/70 font-mono">
            Lingkup sandbox — order dieksekusi via SandboxBroker, saldo & P&L
            bersifat virtual. Harga mengikuti data pasar terkini.
          </p>
        </>
      )}

      {selling && (
        <SellModal
          holding={selling}
          workspaceId={workspaceId!}
          onClose={() => setSelling(null)}
          onSold={() => { setSelling(null); load(); }}
        />
      )}
    </div>
  );
}

function SellModal({
  holding, workspaceId, onClose, onSold,
}: {
  holding: HoldingView;
  workspaceId: string;
  onClose: () => void;
  onSold: () => void;
}) {
  const [qty, setQty] = useState<string>(String(holding.quantity));
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const qtyNum = Number(qty);
  const valid = qtyNum > 0 && qtyNum <= holding.quantity && pin.length >= 6;
  const estProceeds = holding.last_price != null ? qtyNum * holding.last_price : null;

  async function submit() {
    if (!valid) return;
    setLoading(true);
    setError(null);
    try {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      const res = await api.sellHolding(
        holding.ticker, workspaceId, { quantity: qtyNum, pin }, session.access_token,
      );
      toast.success(
        `Terjual ${holding.ticker}: ${idr(res.proceeds)} (P&L ${signed(res.realized_pnl)})`,
      );
      onSold();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menjual.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-background/80 backdrop-blur-md flex items-center justify-center z-50 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-glass border border-border shadow-[0_20px_60px_rgba(0,0,0,0.5)] rounded-2xl p-6 w-full max-w-sm backdrop-blur-xl relative z-10"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-foreground font-bold text-lg mb-1 tracking-tight">
          Jual {holding.ticker}
        </h2>
        <p className="text-muted-foreground text-xs mb-4">
          Dimiliki {holding.quantity.toLocaleString("id-ID", { maximumFractionDigits: 2 })} @ {idr(holding.avg_cost)}
          {holding.last_price != null && <> · harga kini {idr(holding.last_price)}</>}
        </p>

        <label className="block text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
          Jumlah dijual
        </label>
        <input
          type="number"
          value={qty}
          min={0}
          max={holding.quantity}
          onChange={(e) => setQty(e.target.value)}
          className="w-full font-mono bg-secondary border border-border rounded-xl px-4 py-2.5 text-foreground focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all mb-1"
        />
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => setQty(String(holding.quantity))}
            className="text-[10px] text-chart-2 font-mono hover:underline"
          >
            Jual semua
          </button>
          {estProceeds != null && (
            <span className="text-[10px] text-muted-foreground font-mono">
              ≈ {idr(estProceeds)}
            </span>
          )}
        </div>

        <label className="block text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
          PIN keamanan
        </label>
        <input
          type="password"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={8}
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
          className="w-full text-center tracking-[0.6em] font-mono font-bold bg-secondary border border-border rounded-xl px-4 py-2.5 text-foreground placeholder:text-muted-foreground/50 placeholder:tracking-normal focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all"
          placeholder="••••••"
        />
        {error && <p className="text-xs text-rose-400 mt-2 font-medium">{error}</p>}

        <div className="flex gap-3 mt-5">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl border border-border bg-secondary text-foreground text-sm font-semibold hover:bg-secondary/80 transition-all"
          >
            Batal
          </button>
          <button
            disabled={!valid || loading}
            onClick={submit}
            className="flex-1 py-2.5 rounded-xl bg-rose-500 text-white text-sm font-semibold hover:bg-rose-500/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all"
          >
            {loading ? "Menjual…" : "Jual"}
          </button>
        </div>
      </div>
    </div>
  );
}
