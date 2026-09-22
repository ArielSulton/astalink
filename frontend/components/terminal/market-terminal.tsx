"use client";

import { useEffect, useMemo, useState } from "react";

import { useWorkspace } from "@/components/workspace-context";
import { api, type ChartData, type TickerChartData } from "@/lib/api-client";
import { useChartType } from "@/lib/hooks/use-chart-type";
import { useIndicators } from "@/lib/hooks/use-indicators";
import { useScale } from "@/lib/hooks/use-scale";
import { useSidebarCollapsed } from "@/lib/hooks/use-sidebar-collapsed";
import { useTimeframe } from "@/lib/hooks/use-timeframe";
import { createClient } from "@/lib/supabase/client";

import { BusinessConditionPanel } from "./business-condition-panel";
import { ChartToolbar } from "./chart-toolbar";
import { MainChartArea } from "./main-chart-area";
import { MobileWatchlistSheet } from "./mobile-watchlist-sheet";
import { SubplotTabs } from "./subplot-tabs";
import { TerminalHeader } from "./terminal-header";
import { WatchlistSidebar } from "./watchlist-sidebar";

const DEFAULT_WATCHLIST = ["BBCA.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"];

export function MarketTerminal() {
  const { workspaceId } = useWorkspace();
  const [workspaceName, setWorkspaceName] = useState<string | null>(null);

  // Watchlist (sidebar summaries) + selection
  const [watchlist, setWatchlist] = useState<TickerChartData[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>(
    DEFAULT_WATCHLIST[0],
  );
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
        const data = await api.getWatchlist(
          DEFAULT_WATCHLIST,
          config.period,
          config.interval,
        );
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
    return () => {
      cancel = true;
      clearInterval(interval);
    };
  }, [config.period, config.interval, pollPaused]);

  // Keyboard navigation
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey) return;
      const index = DEFAULT_WATCHLIST.indexOf(selectedTicker);
      switch (event.key) {
        case "ArrowLeft":
          event.preventDefault();
          setSelectedTicker(DEFAULT_WATCHLIST[Math.max(0, index - 1)]);
          break;
        case "ArrowRight":
          event.preventDefault();
          setSelectedTicker(
            DEFAULT_WATCHLIST[
              Math.min(DEFAULT_WATCHLIST.length - 1, index + 1)
            ],
          );
          break;
        case "l":
        case "L":
          setScale(scale === "linear" ? "log" : "linear");
          break;
        case " ":
          event.preventDefault();
          setPollPaused((paused) => !paused);
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
      const {
        data: { session },
      } = await sb.auth.getSession();
      if (!session) return;
      try {
        const nextChart = await api.getChart(
          selectedTicker,
          config.period,
          config.interval,
          session.access_token,
        );
        if (!cancel) setChart(nextChart);
      } catch {
        if (!cancel) setChart(null);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [selectedTicker, config.period, config.interval]);

  // Workspace name
  useEffect(() => {
    if (!workspaceId) return;
    const sb = createClient();
    (async () => {
      const {
        data: { session },
      } = await sb.auth.getSession();
      if (!session) return;
      try {
        const workspace = await sb
          .from("workspaces")
          .select("name")
          .eq("id", workspaceId)
          .single();
        setWorkspaceName(workspace.data?.name ?? null);
      } catch {
        /* noop */
      }
    })();
  }, [workspaceId]);

  const selectedSym = selectedTicker.replace(".JK", "");
  const selectedData =
    watchlist.find((ticker) => ticker.ticker === selectedTicker) ?? null;

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
    return order
      .filter((id) => indicators.includes(id as never))
      .map((id) => map[id]);
  }, [indicators]);

  const chartData = chart?.price_series ?? [];
  const chartLastClose = chart?.last_close ?? selectedData?.last_close ?? null;
  const chartPct =
    chart?.price_change_pct ?? selectedData?.price_change_pct ?? null;

  return (
    <div className="min-h-full bg-background">
      <h1 className="sr-only">Pasar &amp; Grafik</h1>

      {/* Row 2: Terminal header */}
      <TerminalHeader workspaceName={workspaceName} />

      {/* Row 3: Terminal (sidebar + chart) */}
      <div className="grid min-h-0 grid-cols-[auto_1fr] border-b border-border">
        <div className="hidden lg:block">
          <WatchlistSidebar
            watchlist={watchlist}
            selectedTicker={selectedTicker}
            onSelect={setSelectedTicker}
            collapsed={collapsed}
            onToggle={() => setCollapsed(!collapsed)}
            loading={marketLoading}
          />
        </div>
        <main aria-label="Grafik pasar" className="flex min-w-0 flex-col">
          <MobileWatchlistSheet
            watchlist={watchlist}
            selectedTicker={selectedTicker}
            onSelect={setSelectedTicker}
            collapsed={collapsed}
            onToggle={() => setCollapsed(!collapsed)}
            loading={marketLoading}
          />
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
          <div className="flex-1 space-y-3 p-3 sm:p-4">
            <MainChartArea
              data={chartData}
              indicators={indicators}
              chartType={chartType}
              scale={scale}
              lastClose={chartLastClose}
              priceChangePct={chartPct}
            />
            {subplots.length > 0 &&
              subplots.some((subplot) => subplot.id !== "volume") && (
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
