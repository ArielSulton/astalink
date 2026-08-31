"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, ArrowLeftRight, ClipboardCheck, FileText, LineChart, MessageSquare, TrendingUp, Wallet } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { useWorkspace } from "@/components/workspace-context";
import dynamic from "next/dynamic";
const PriceChart = dynamic(() => import("@/components/price-chart").then(m => ({ default: m.PriceChart })), { ssr: false, loading: () => <div className="h-64 flex items-center justify-center text-muted-foreground text-xs font-mono">Memuat chart…</div> });
import { TickerCard } from "@/components/ticker-card";
import { createClient } from "@/lib/supabase/client";
import { api, type PortfolioResponse, type TickerChartData } from "@/lib/api-client";

const DEFAULT_WATCHLIST = ["BBCA.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"];

const QUICK_ACTIONS = [
  { label: "Chat AI", description: "Tanya analisis & alokasi", href: "/chatbot", icon: MessageSquare, color: "text-chart-2" },
  { label: "Approvals", description: "Setujui transaksi", href: "/approvals", icon: ClipboardCheck, color: "text-chart-1" },
  { label: "Transaksi", description: "Riwayat perdagangan", href: "/transactions", icon: ArrowLeftRight, color: "text-chart-3" },
  { label: "Dokumen Legal", description: "Unggah & kelola", href: "/legal-docs", icon: FileText, color: "text-chart-4" },
];

function fmtIdr(n: number | null | undefined): string {
  if (n == null) return "—";
  return "Rp " + n.toLocaleString("id-ID", { maximumFractionDigits: 0 });
}

function fmtSigned(n: number | null | undefined): string {
  if (n == null) return "—";
  const s = Math.abs(n).toLocaleString("id-ID", { maximumFractionDigits: 0 });
  return (n >= 0 ? "+Rp " : "-Rp ") + s;
}

function MiniStat({ label, value, tone }: { label: string; value: string; tone?: number | null }) {
  const toneClass = tone == null ? "text-foreground" : tone >= 0 ? "text-chart-2" : "text-destructive";
  return (
    <div className="rounded-xl border border-border bg-card px-4 py-3">
      <p className="text-[9px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
        {label}
      </p>
      <p className={`font-mono text-base font-bold tabular-nums leading-none ${toneClass}`}>{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const [watchlist, setWatchlist] = useState<TickerChartData[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>(DEFAULT_WATCHLIST[0]);
  const [marketLoading, setMarketLoading] = useState(true);

  const { workspaceId } = useWorkspace();
  const [cashBalance, setCashBalance] = useState<number | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);

  useEffect(() => {
    api
      .getWatchlist(DEFAULT_WATCHLIST)
      .then((data) => setWatchlist(data))
      .catch(() => {})
      .finally(() => setMarketLoading(false));
  }, []);

  // Saldo kas sandbox milik workspace terpilih (RLS-scoped).
  useEffect(() => {
    if (!workspaceId) return;
    const sb = createClient();
    sb.from("workspaces")
      .select("cash_balance")
      .eq("id", workspaceId)
      .single()
      .then(({ data }) => {
        setCashBalance(data?.cash_balance != null ? Number(data.cash_balance) : null);
      });
  }, [workspaceId]);

  // Sandbox portfolio summary (holdings + P&L).
  useEffect(() => {
    if (!workspaceId) return;
    (async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      try {
        setPortfolio(await api.getPortfolio(workspaceId, session.access_token));
      } catch {
        setPortfolio(null);
      }
    })();
  }, [workspaceId]);

  const selectedData = watchlist.find((t) => t.ticker === selectedTicker) ?? null;

  return (
    <div className="min-h-full bg-background">
      {/* Portfolio summary strip */}
      {portfolio && portfolio.holdings.length > 0 && (
        <div className="border-b border-border px-6 py-5 bg-card/20 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <div className="flex size-8 items-center justify-center rounded-lg bg-chart-2/10 border border-chart-2/25">
                <LineChart className="size-4 text-chart-2" />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground font-mono">
                Portofolio
              </span>
            </div>
            <Link
              href="/portfolio"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-chart-2 hover:text-chart-2/80 transition-colors"
            >
              Lihat detail <ArrowRight className="size-3" />
            </Link>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MiniStat label="Total Ekuitas" value={fmtIdr(portfolio.total_equity)} />
            <MiniStat label="Kas" value={fmtIdr(portfolio.cash_balance)} />
            <MiniStat label="Unrealized P&L" value={fmtSigned(portfolio.total_unrealized_pnl)}
              tone={portfolio.total_unrealized_pnl} />
            <MiniStat label="Realized P&L" value={fmtSigned(portfolio.total_realized_pnl)}
              tone={portfolio.total_realized_pnl} />
          </div>
          <div className="flex flex-wrap gap-1.5 mt-3">
            {portfolio.holdings.slice(0, 6).map((h) => (
              <span key={h.ticker}
                className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-secondary border border-border text-muted-foreground">
                {h.ticker}
              </span>
            ))}
            {portfolio.holdings.length > 6 && (
              <span className="text-[10px] font-mono text-muted-foreground/60 px-1 py-0.5">
                +{portfolio.holdings.length - 6}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="border-b border-border px-6 py-5 bg-card/10">
        <div className="flex items-center gap-2.5 mb-4">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 border border-primary/25">
            <TrendingUp className="size-4 text-primary" />
          </div>
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground font-mono">
            Akses Cepat
          </span>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {QUICK_ACTIONS.map((action) => (
            <Link
              key={action.label}
              href={action.href}
              className="group flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 hover:border-primary/40 hover:bg-primary/[0.03] transition-all duration-200"
            >
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-secondary border border-border group-hover:border-primary/30 transition-colors">
                <action.icon className={`size-4 ${action.color}`} />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground leading-tight truncate">{action.label}</p>
                <p className="text-[10px] text-muted-foreground leading-tight truncate">{action.description}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Market Watch Header */}
      <div className="border-b border-border px-6 py-5 bg-card/30">
        <PageHeader eyebrow="Pantauan Pasar" title="IDX Blue Chips" className="mb-5">
          {cashBalance != null && (
            <div className="flex items-center gap-2.5 rounded-xl border border-border bg-card px-3.5 py-1.5 animate-fade-in">
              <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-chart-2/10 border border-chart-2/25">
                <Wallet className="size-3.5 text-chart-2" />
              </div>
              <div className="leading-tight">
                <p className="text-[9px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
                  Saldo
                </p>
                <p className="font-mono text-sm font-bold text-foreground tabular-nums">
                  Rp {cashBalance.toLocaleString("id-ID", { maximumFractionDigits: 0 })}
                </p>
              </div>
            </div>
          )}
        </PageHeader>

        <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
          {DEFAULT_WATCHLIST.map((ticker) => {
            const data = watchlist.find((t) => t.ticker === ticker);
            return (
              <TickerCard
                key={ticker}
                ticker={ticker}
                lastClose={marketLoading ? null : (data?.last_close ?? null)}
                priceChangePct={marketLoading ? null : (data?.price_change_pct ?? null)}
                rsi14={marketLoading ? null : (data?.rsi14 ?? null)}
                series={marketLoading ? null : (data?.price_series.map((p) => p.close) ?? null)}
                selected={selectedTicker === ticker}
                onClick={() => setSelectedTicker(ticker)}
              />
            );
          })}
        </div>
      </div>

      {/* Chart Area */}
      <div className="px-6 py-5">
        <div className="flex items-center gap-2.5 mb-4">
          <div className="flex size-8 items-center justify-center rounded-lg bg-chart-2/10 border border-chart-2/25">
            <LineChart className="size-4 text-chart-2" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground font-mono">
              {selectedTicker}
            </p>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card/50 p-4">
          {marketLoading ? (
            <div className="h-64 flex items-center justify-center text-muted-foreground text-xs font-mono tracking-wider">
              <span className="w-2 h-2 rounded-full bg-chart-2 animate-ping mr-2.5" />
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
      </div>
    </div>
  );
}
