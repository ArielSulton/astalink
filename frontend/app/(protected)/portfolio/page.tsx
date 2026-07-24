"use client";
import { useCallback, useEffect, useState } from "react";
import { PiggyBank, TrendingUp, Wallet, LineChart, PlusCircle, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { toast } from "sonner";
import { api, type PortfolioResponse, type HoldingView } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { useWorkspace } from "@/components/workspace-context";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { StatCard } from "@/components/ui/stat-card";
import { Button } from "@/components/ui/button";

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
  const [buying, setBuying] = useState<boolean>(false);
  const [buyTicker, setBuyTicker] = useState<string>("");

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

  const handleOpenBuy = (ticker?: string) => {
    setBuyTicker(ticker || "");
    setBuying(true);
  };

  return (
    <div className="p-8 space-y-6 max-w-6xl w-full mx-auto bg-background min-h-screen text-foreground">
      <PageHeader
        eyebrow="Sandbox Portfolio & Allocation"
        title="Portofolio Investasi"
        className="border-b border-border pb-5"
      >
        {workspaceId && (
          <Button onClick={() => handleOpenBuy()} className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold">
            <PlusCircle className="h-4 w-4 mr-2" />
            Alokasikan Dana / Beli Saham
          </Button>
        )}
      </PageHeader>

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
            <StatCard label="Saldo Kas Tunai" value={idr(data.cash_balance)} icon={PiggyBank}
              hint="Sisa kas yang dapat dialokasikan" />
            <StatCard label="Unrealized P&L" value={signed(data.total_unrealized_pnl)}
              icon={TrendingUp} hint="Selisih nilai pasar vs modal awal"
              className={data.total_unrealized_pnl != null && data.total_unrealized_pnl < 0
                ? "border-rose-500/20" : ""} />
            <StatCard label="Realized P&L" value={signed(data.total_realized_pnl)}
              icon={Wallet} hint="Akumulasi hasil penjualan" />
          </div>

          <div className="rounded-2xl border border-border bg-card overflow-hidden shadow-xl">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
                Rincian Kepemilikan & Kinerja Investasi
              </h2>
              {loading && <span className="text-[10px] text-muted-foreground font-mono">memuat…</span>}
            </div>

            {!hasHoldings ? (
              <div className="p-8">
                <EmptyState icon={TrendingUp} title="Belum Ada Kepemilikan Saham">
                  Portofolio masih kosong. Klik tombol <strong>"Alokasikan Dana / Beli Saham"</strong> di atas
                  atau gunakan Asisten AI untuk memulai alokasi investasi.
                </EmptyState>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-secondary/40 text-left text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
                      <th className="px-5 py-3">Saham</th>
                      <th className="px-4 py-3 text-right">Modal Awal Invest</th>
                      <th className="px-4 py-3 text-right">Harga Awal</th>
                      <th className="px-4 py-3 text-right">Harga Sekarang</th>
                      <th className="px-4 py-3 text-right">Nilai Pasar</th>
                      <th className="px-4 py-3 text-right">Persentase Kenaikan / Retur</th>
                      <th className="px-4 py-3 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.holdings.map((h) => {
                      const pct = h.unrealized_pnl_pct != null ? h.unrealized_pnl_pct * 100 : null;
                      const isGain = pct != null && pct >= 0;
                      return (
                        <tr key={h.ticker} className="border-b border-border/60 last:border-0 hover:bg-secondary/20 transition-colors">
                          <td className="px-5 py-4">
                            <span className="font-mono font-bold text-base block">{h.ticker}</span>
                            <span className="text-[11px] text-muted-foreground font-mono">
                              {h.quantity.toLocaleString("id-ID", { maximumFractionDigits: 2 })} lembar
                            </span>
                          </td>
                          <td className="px-4 py-4 text-right font-mono tabular-nums font-semibold">
                            {idr(h.cost_basis)}
                          </td>
                          <td className="px-4 py-4 text-right font-mono tabular-nums text-muted-foreground">
                            {idr(h.avg_cost)}
                          </td>
                          <td className="px-4 py-4 text-right font-mono tabular-nums font-semibold">
                            {idr(h.last_price)}
                          </td>
                          <td className="px-4 py-4 text-right font-mono tabular-nums font-bold">
                            {idr(h.market_value)}
                          </td>
                          <td className="px-4 py-4 text-right">
                            <div className={`inline-flex flex-col items-end ${pnlClass(h.unrealized_pnl)}`}>
                              <span className="font-mono tabular-nums font-bold flex items-center gap-1 text-sm">
                                {isGain ? (
                                  <ArrowUpRight className="h-4 w-4 shrink-0 text-emerald-400" />
                                ) : (
                                  <ArrowDownRight className="h-4 w-4 shrink-0 text-rose-400" />
                                )}
                                {pct != null ? `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%` : "—"}
                              </span>
                              <span className="text-xs font-mono opacity-80 font-medium">
                                {signed(h.unrealized_pnl)}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleOpenBuy(h.ticker)}
                                className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 transition-all"
                              >
                                Tambah
                              </button>
                              <button
                                onClick={() => setSelling(h)}
                                className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-rose-500/30 text-rose-400 hover:bg-rose-500/10 transition-all"
                              >
                                Jual
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <p className="text-[10px] text-muted-foreground/70 font-mono">
            Setiap alokasi dana akan secara otomatis mengurangi Saldo Kas dan menambahkan posisi saham ke dalam Portofolio.
            Harga saham diperbarui berdasarkan data pasar terkini.
          </p>
        </>
      )}

      {buying && (
        <BuyModal
          workspaceId={workspaceId!}
          initialTicker={buyTicker}
          availableCash={data?.cash_balance ?? 0}
          onClose={() => setBuying(false)}
          onBought={() => { setBuying(false); load(); }}
        />
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

function BuyModal({
  workspaceId, initialTicker, availableCash, onClose, onBought,
}: {
  workspaceId: string;
  initialTicker: string;
  availableCash: number;
  onClose: () => void;
  onBought: () => void;
}) {
  const [ticker, setTicker] = useState(initialTicker);
  const [amountStr, setAmountStr] = useState<string>("10000000"); // default 10 Juta
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const amountNum = Number(amountStr);
  const valid = ticker.trim().length >= 3 && amountNum > 0 && amountNum <= availableCash;

  const presetAmounts = [
    { label: "5 Juta", val: 5000000 },
    { label: "10 Juta", val: 10000000 },
    { label: "25 Juta", val: 25000000 },
    { label: "50 Juta", val: 50000000 },
  ];

  async function submit() {
    if (!valid) return;
    setLoading(true);
    setError(null);
    try {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;

      const res = await api.buyHolding(
        workspaceId,
        { ticker: ticker.toUpperCase().trim(), amount: amountNum },
        session.access_token,
      );

      toast.success(
        `Berhasil mengalokasikan ${idr(res.allocated_amount)} ke ${res.ticker}! Saldo kas tersisa: ${idr(res.cash_balance)}`,
      );
      onBought();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal melakukan alokasi dana.");
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
        className="bg-glass border border-border shadow-[0_20px_60px_rgba(0,0,0,0.5)] rounded-2xl p-6 w-full max-w-md backdrop-blur-xl relative z-10 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <h2 className="text-foreground font-bold text-lg tracking-tight">
            Alokasikan Dana Ke Saham
          </h2>
          <p className="text-muted-foreground text-xs mt-0.5">
            Saldo Kas Tersedia: <strong className="text-foreground font-mono">{idr(availableCash)}</strong>
          </p>
        </div>

        <div>
          <label className="block text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
            Kode Saham (Ticker)
          </label>
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="Contoh: BBCA, TLKM, ASII, BBRI"
            className="w-full font-mono uppercase font-bold bg-secondary border border-border rounded-xl px-4 py-2.5 text-foreground focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/20 transition-all"
          />
        </div>

        <div>
          <label className="block text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
            Nominal Alokasi (Rupiah)
          </label>
          <input
            type="number"
            value={amountStr}
            onChange={(e) => setAmountStr(e.target.value)}
            placeholder="Nominal alokasi dalam Rp"
            className="w-full font-mono font-bold bg-secondary border border-border rounded-xl px-4 py-2.5 text-foreground focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/20 transition-all mb-2"
          />
          <div className="flex items-center gap-2 flex-wrap">
            {presetAmounts.map((p) => (
              <button
                key={p.val}
                type="button"
                onClick={() => setAmountStr(String(p.val))}
                className="text-[11px] font-mono px-2.5 py-1 rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-muted-foreground hover:text-foreground transition-all"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {amountNum > availableCash && (
          <p className="text-xs text-rose-400 font-medium">
            ⚠ Nominal alokasi melebihi saldo kas yang tersedia.
          </p>
        )}

        {error && <p className="text-xs text-rose-400 font-medium">{error}</p>}

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl border border-border bg-secondary text-foreground text-sm font-semibold hover:bg-secondary/80 transition-all"
          >
            Batal
          </button>
          <button
            type="button"
            disabled={!valid || loading}
            onClick={submit}
            className="flex-1 py-2.5 rounded-xl bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all"
          >
            {loading ? "Mengalokasikan…" : "Alokasikan Dana"}
          </button>
        </div>
      </div>
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
          Jumlah dijual (lembar)
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

