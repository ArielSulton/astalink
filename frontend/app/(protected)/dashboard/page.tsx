"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, LineChart } from "lucide-react";
import { useWorkspace } from "@/components/workspace-context";
import { createClient } from "@/lib/supabase/client";
import { api, type PortfolioResponse, type TickerChartData, type ChartData } from "@/lib/api-client";
import {
  TerminalHeader, WatchlistSidebar, ChartToolbar, MainChartArea, SubplotTabs, BusinessConditionPanel,
} from "@/components/terminal";
import { useTimeframe } from "@/lib/hooks/use-timeframe";
import { useIndicators } from "@/lib/hooks/use-indicators";
import { useChartType } from "@/lib/hooks/use-chart-type";
import { useScale } from "@/lib/hooks/use-scale";
import { useSidebarCollapsed } from "@/lib/hooks/use-sidebar-collapsed";

const DEFAULT_WATCHLIST = ["BBCA.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"];

function fmtIdr(v: number | null | undefined): string {
  if (v == null) return "—";
  return "Rp " + v.toLocaleString("id-ID", { maximumFractionDigits: 0 });
}

function fmtSigned(v: number | null | undefined): string {
  if (v == null) return "—";
  const s = v.toLocaleString("id-ID", { maximumFractionDigits: 0 });
  return (v >= 0 ? "+Rp " : "-Rp ") + s.replace("-", "");
}

function MiniStat({ label, value, tone }: { label: string; value: string; tone?: number | null }) {
  const toneClass = tone == null ? "text-foreground" : tone >= 0 ? "text-chart-2" : "text-destructive";
  return (
    <div className="rounded-xl border border-border bg-card px-4 py-3">
      <p className="text-[9px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1.5">{label}</p>
      <p className={`font-mono text-base font-bold tabular-nums leading-none ${toneClass}`}>{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const { workspaceId } = useWorkspace();
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [cashBalance, setCashBalance] = useState<number | null>(null);
  const [workspaceName, setWorkspaceName] = useState<string | null>(null);

  // Watchlist (sidebar summaries) + selection
  const [watchlist, setWatchlist] = useState<TickerChartData[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>(DEFAULT_WATCHLIST[0]);
  const [marketLoading, setMarketLoading] = useState(true);

  // Chart series for the SELECTED ticker (full indicator data)
  const [chart, setChart] = useState<ChartData | null>(null);

  // Terminal state (persisted)
  const { setTimeframe, config } = useTimeframe();
  const { indicators, toggle } = useIndicators();
  const { chartType, setChartType } = useChartType();
  const { scale, setScale } = useScale();
  const { collapsed, setCollapsed } = useSidebarCollapsed();

  // Poll pause state
  const [pollPaused, setPollPaused] = useState(false);

  // Watchlist: 30s polling
  useEffect(() => {
    let cancel = false;
    const fetchWatchlist = async () => {
      if (pollPaused) return;
      try {
        const data = await api.getWatchlist(DEFAULT_WATCHLIST, config.period, config.interval);
        if (cancel) return;
        setWatchlist(data);
      } catch {
        /* noop */
      } finally {
        if (!cancel) setMarketLoading(false);
      }
    };
    fetchWatchlist();
    const interval = setInterval(fetchWatchlist, 30000);
    return () => { cancel = true; clearInterval(interval); };
  }, [config.period, config.interval, pollPaused]);

  // Keyboard navigation
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey) return;
      const idx = DEFAULT_WATCHLIST.indexOf(selectedTicker);
      switch (e.key) {
        case "ArrowLeft":
          e.preventDefault();
          setSelectedTicker(DEFAULT_WATCHLIST[Math.max(0, idx - 1)]);
          break;
        case "ArrowRight":
          e.preventDefault();
          setSelectedTicker(DEFAULT_WATCHLIST[Math.min(DEFAULT_WATCHLIST.length - 1, idx + 1)]);
          break;
        case "l":
        case "L":
          setScale(scale === "linear" ? "log" : "linear");
          break;
        case " ":
          e.preventDefault();
          setPollPaused((p) => !p);
          break;
        default:
          break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedTicker, scale, setScale]);

  // Chart series for the selected ticker: fetch whenever selection or timeframe changes
  useEffect(() => {
    let cancel = false;
    (async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      try {
        const c = await api.getChart(selectedTicker, config.period, config.interval, session.access_token);
        if (!cancel) { setChart(c); }
      } catch {
        if (!cancel) { setChart(null); }
      }
    })();
    return () => { cancel = true; };
  }, [selectedTicker, config.period, config.interval]);

  // Portfolio + cash + workspace name
  useEffect(() => {
    if (!workspaceId) return;
    const sb = createClient();
    (async () => {
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      try {
        const [p, wsRows] = await Promise.all([
          api.getPortfolio(workspaceId, session.access_token),
          sb.from("workspaces").select("name").eq("id", workspaceId).single(),
        ]);
        setPortfolio(p);
        setWorkspaceName(wsRows.data?.name ?? null);
        setCashBalance(p ? p.cash_balance : null);
      } catch {
        /* noop */
      }
    })();
  }, [workspaceId]);

  const selectedSym = selectedTicker.replace(".JK", "");
  const selectedData = watchlist.find((t) => t.ticker === selectedTicker) ?? null;

  // Build subplots from enabled momentum/volume indicators
  const subplots = useMemo(() => {
    const map: Record<string, { id: string; label: string }> = {
      volume: { id: "volume", label: "Volume" },
      rsi: { id: "rsi", label: "RSI" },
      macd: { id: "macd", label: "MACD" },
      atr: { id: "atr", label: "ATR" },
      stoch: { id: "stoch", label: "Stoch" },
      obv: { id: "obv", label: "OBV" },
    };
    const order = ["volume", "rsi", "macd", "atr", "stoch", "obv"];
    return order.filter((id) => indicators.includes(id as never)).map((id) => map[id]);
  }, [indicators]);

  const chartData = chart?.price_series ?? [];
  const chartLastClose = chart?.last_close ?? selectedData?.last_close ?? null;
  const chartPct = chart?.price_change_pct ?? selectedData?.price_change_pct ?? null;

  return (
    <div className="min-h-full bg-background">
      {/* Hidden per concept change (2026-09) — Portfolio strip (incl. Kas/saldo
         ministat) removed from dashboard along with the /portfolio nav entry.
      {portfolio && portfolio.holdings.length > 0 && (
        <div className="border-b border-border px-6 py-5 bg-card/20">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <div className="flex size-8 items-center justify-center rounded-lg bg-chart-2/10 border border-chart-2/25">
                <LineChart className="size-4 text-chart-2" />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground font-mono">
                Portofolio
              </span>
            </div>
            <Link href="/portfolio" className="inline-flex items-center gap-1.5 text-xs font-medium text-chart-2 hover:text-chart-2/80 transition-colors">
              Lihat detail <ArrowRight className="size-3" />
            </Link>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MiniStat label="Total Ekuitas" value={fmtIdr(portfolio.total_equity)} />
            <MiniStat label="Kas" value={fmtIdr(portfolio.cash_balance)} />
            <MiniStat label="Unrealized P&L" value={fmtSigned(portfolio.total_unrealized_pnl)} tone={portfolio.total_unrealized_pnl} />
            <MiniStat label="Realized P&L" value={fmtSigned(portfolio.total_realized_pnl)} tone={portfolio.total_realized_pnl} />
          </div>
        </div>
      )}
      */}

      {/* Row 2: Terminal header */}
      <TerminalHeader cashBalance={cashBalance} workspaceName={workspaceName} />

      {/* Row 3: Terminal (sidebar + chart) */}
      <div className="grid grid-cols-[auto_1fr] min-h-0 border-b border-border">
        <WatchlistSidebar
          watchlist={watchlist}
          selectedTicker={selectedTicker}
          onSelect={setSelectedTicker}
          collapsed={collapsed}
          onToggle={() => setCollapsed(!collapsed)}
          loading={marketLoading}
        />
        <main className="flex min-w-0 flex-col">
          <ChartToolbar
            ticker={selectedTicker}
            symLabel={selectedSym}
            timeframe={config}
            onTimeframeChange={setTimeframe}
            indicators={indicators}
            onToggleIndicator={toggle}
            chartType={chartType}
            onChartTypeChange={setChartType}
            scale={scale}
            onScaleChange={setScale}
            onExport={() => undefined}
          />
          <div className="flex-1 space-y-3 p-4">
            <MainChartArea
              data={chartData}
              indicators={indicators}
              chartType={chartType}
              scale={scale}
              lastClose={chartLastClose}
              priceChangePct={chartPct}
            />
            {subplots.length > 0 && subplots.some((s) => s.id !== "volume") && (
              <SubplotTabs data={chartData} subplots={subplots} />
            )}
          </div>
        </main>
      </div>

      {/* Row 4: Business condition */}
      <BusinessConditionPanel />
    </div>
  );
}