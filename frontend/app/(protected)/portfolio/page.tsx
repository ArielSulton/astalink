"use client";

import { LineChart, PiggyBank, PlusCircle, TrendingUp, Wallet } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { AllocationBuyModal } from "@/components/allocation-buy-modal";
import { HoldingsView } from "@/components/portfolio/holdings-view";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { ResponsiveDialog } from "@/components/ui/responsive-dialog";
import { StatCard } from "@/components/ui/stat-card";
import { useWorkspace } from "@/components/workspace-context";
import { api, type HoldingView, type PortfolioResponse } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

function idr(value: number | null | undefined): string {
  if (value == null) return "—";
  return `Rp ${value.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;
}

function signed(value: number | null | undefined): string {
  if (value == null) return "—";
  const formatted = value.toLocaleString("id-ID", { maximumFractionDigits: 0 });
  return `${value >= 0 ? "+Rp " : "-Rp "}${formatted.replace("-", "")}`;
}

export default function PortfolioPage() {
  const { workspaceId } = useWorkspace();
  const [data, setData] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selling, setSelling] = useState<HoldingView | null>(null);
  const [buying, setBuying] = useState(false);
  const [buyTicker, setBuyTicker] = useState("");

  const load = useCallback(async () => {
    if (!workspaceId) {
      setData(null);
      return;
    }
    setLoading(true);
    try {
      const sb = createClient();
      const {
        data: { session },
      } = await sb.auth.getSession();
      if (!session) return;
      const response = await api.getPortfolio(
        workspaceId,
        session.access_token,
      );
      setData(response);
    } catch {
      toast.error("Gagal memuat portofolio.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const hasHoldings = data && data.holdings.length > 0;

  const handleOpenBuy = (ticker?: string) => {
    setBuyTicker(ticker || "");
    setBuying(true);
  };

  const handleOpenSell = (ticker: string) => {
    const holding = data?.holdings.find((item) => item.ticker === ticker);
    if (holding) setSelling(holding);
  };

  return (
    <div className="mx-auto min-h-screen w-full max-w-6xl space-y-6 bg-background p-4 text-foreground sm:p-6 lg:p-8">
      <PageHeader
        eyebrow="Sandbox Portofolio & Alokasi"
        title="Portofolio Investasi"
        className="border-b border-border pb-5"
      >
        {workspaceId && (
          <Button onClick={() => handleOpenBuy()} className="font-semibold">
            <PlusCircle className="mr-2 size-4" />
            Alokasikan Dana / Beli Saham
          </Button>
        )}
      </PageHeader>

      {!workspaceId && (
        <EmptyState icon={Wallet} title="Pilih Workspace">
          Pilih workspace di bagian atas untuk melihat portofolio Anda.
        </EmptyState>
      )}

      {workspaceId && loading && !data && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[0, 1, 2, 3].map((item) => (
              <div
                key={item}
                className="h-28 animate-pulse rounded-xl bg-card ring-1 ring-foreground/10"
              />
            ))}
          </div>
          <div className="h-64 animate-pulse rounded-xl bg-card ring-1 ring-foreground/10" />
        </div>
      )}

      {workspaceId && data && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard
              label="Total Ekuitas"
              value={idr(data.total_equity)}
              icon={LineChart}
              hint="Kas + nilai pasar holdings"
            />
            <StatCard
              label="Saldo Kas Tunai"
              value={idr(data.cash_balance)}
              icon={PiggyBank}
              hint="Sisa kas yang dapat dialokasikan"
            />
            <StatCard
              label="Unrealized P&L"
              value={signed(data.total_unrealized_pnl)}
              icon={TrendingUp}
              hint="Selisih nilai pasar vs modal awal"
              className={
                data.total_unrealized_pnl != null &&
                data.total_unrealized_pnl < 0
                  ? "border-destructive/20"
                  : ""
              }
            />
            <StatCard
              label="Realized P&L"
              value={signed(data.total_realized_pnl)}
              icon={Wallet}
              hint="Akumulasi hasil penjualan"
            />
          </div>

          <section className="overflow-hidden rounded-xl bg-card ring-1 ring-foreground/10">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Rincian Kepemilikan & Kinerja Investasi
              </h2>
              {loading && (
                <span className="font-mono text-[10px] text-muted-foreground">
                  memuat…
                </span>
              )}
            </div>

            {!hasHoldings ? (
              <div className="p-8">
                <EmptyState
                  icon={TrendingUp}
                  title="Belum Ada Kepemilikan Saham"
                >
                  Portofolio masih kosong. Gunakan tombol alokasi dana di atas
                  atau Tanya Asta untuk memulai.
                </EmptyState>
              </div>
            ) : (
              <HoldingsView
                holdings={data.holdings}
                totalEquity={data.total_equity}
                onBuy={handleOpenBuy}
                onSell={handleOpenSell}
              />
            )}
          </section>

          <p className="font-mono text-[10px] text-muted-foreground/70">
            Setiap alokasi dana otomatis mengurangi saldo kas dan menambahkan
            posisi saham. Harga diperbarui berdasarkan data pasar terkini.
          </p>
        </>
      )}

      {buying && (
        <AllocationBuyModal
          workspaceId={workspaceId!}
          suggestedTickers={buyTicker ? [buyTicker] : []}
          onClose={() => setBuying(false)}
          onSuccess={() => {
            setBuying(false);
            void load();
          }}
        />
      )}

      {selling && (
        <SellModal
          holding={selling}
          workspaceId={workspaceId!}
          onClose={() => setSelling(null)}
          onSold={() => {
            setSelling(null);
            void load();
          }}
        />
      )}
    </div>
  );
}

function SellModal({
  holding,
  workspaceId,
  onClose,
  onSold,
}: {
  holding: HoldingView;
  workspaceId: string;
  onClose: () => void;
  onSold: () => void;
}) {
  const [quantity, setQuantity] = useState(String(holding.quantity));
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const quantityNumber = Number(quantity);
  const valid =
    quantityNumber > 0 && quantityNumber <= holding.quantity && pin.length >= 6;
  const estimatedProceeds =
    holding.last_price != null ? quantityNumber * holding.last_price : null;

  async function submit() {
    if (!valid) return;
    setLoading(true);
    setError(null);
    try {
      const sb = createClient();
      const {
        data: { session },
      } = await sb.auth.getSession();
      if (!session) return;
      const response = await api.sellHolding(
        holding.ticker,
        workspaceId,
        { quantity: quantityNumber, pin },
        session.access_token,
      );
      toast.success(
        `Terjual ${holding.ticker}: ${idr(response.proceeds)} (P&L ${signed(
          response.realized_pnl,
        )})`,
      );
      onSold();
    } catch (caughtError) {
      setError(
        caughtError instanceof Error ? caughtError.message : "Gagal menjual.",
      );
    } finally {
      setLoading(false);
    }
  }

  const description = `Dimiliki ${holding.quantity.toLocaleString("id-ID", {
    maximumFractionDigits: 2,
  })} @ ${idr(holding.avg_cost)}${
    holding.last_price != null ? ` · harga kini ${idr(holding.last_price)}` : ""
  }`;

  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={`Jual ${holding.ticker}`}
      description={description}
    >
      <div className="mt-5 space-y-4">
        <div>
          <label className="mb-1.5 block font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Jumlah dijual (lembar)
          </label>
          <input
            type="number"
            value={quantity}
            min={0}
            max={holding.quantity}
            onChange={(event) => setQuantity(event.target.value)}
            className="w-full rounded-xl border border-border bg-secondary px-4 py-2.5 font-mono text-foreground transition-all focus:border-chart-2 focus:outline-none focus:ring-1 focus:ring-chart-2/20"
          />
          <div className="mt-1 flex items-center justify-between">
            <button
              type="button"
              onClick={() => setQuantity(String(holding.quantity))}
              className="min-h-11 font-mono text-[10px] text-chart-2 hover:underline"
            >
              Jual semua
            </button>
            {estimatedProceeds != null && (
              <span className="font-mono text-[10px] text-muted-foreground">
                ≈ {idr(estimatedProceeds)}
              </span>
            )}
          </div>
        </div>

        <div>
          <label className="mb-1.5 block font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            PIN keamanan
          </label>
          <input
            type="password"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={8}
            value={pin}
            onChange={(event) => setPin(event.target.value.replace(/\D/g, ""))}
            className="w-full rounded-xl border border-border bg-secondary px-4 py-2.5 text-center font-mono font-bold tracking-[0.6em] text-foreground transition-all placeholder:tracking-normal placeholder:text-muted-foreground/50 focus:border-chart-2 focus:outline-none focus:ring-1 focus:ring-chart-2/20"
            placeholder="••••••"
          />
          {error && (
            <p className="mt-2 text-xs font-medium text-destructive">{error}</p>
          )}
        </div>

        <div className="flex gap-3 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="min-h-11 flex-1 rounded-xl border border-border bg-secondary text-sm font-semibold text-foreground transition-all hover:bg-secondary/80"
          >
            Batal
          </button>
          <button
            type="button"
            disabled={!valid || loading}
            onClick={submit}
            className="min-h-11 flex-1 rounded-xl bg-destructive text-sm font-semibold text-white transition-all hover:bg-destructive/90 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground"
          >
            {loading ? "Menjual…" : "Jual"}
          </button>
        </div>
      </div>
    </ResponsiveDialog>
  );
}
