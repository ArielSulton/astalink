"use client";
import { useState } from "react";
import { ChevronsLeft, ChevronsRight, Search } from "lucide-react";
import type { TickerChartData } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface WatchlistSidebarProps {
  watchlist: TickerChartData[];
  selectedTicker: string;
  onSelect: (ticker: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  loading: boolean;
}

function SparklineMini({ series, isUp }: { series: number[]; isUp: boolean }) {
  if (!series || series.length < 2) return null;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const range = max - min || 1;
  const points = series
    .map((v, i) => `${((i / (series.length - 1)) * 100).toFixed(1)},${(26 - ((v - min) / range) * 22).toFixed(1)}`)
    .join(" ");
  const color = isUp ? "var(--color-chart-2)" : "var(--color-destructive)";
  return (
    <svg viewBox="0 0 100 28" preserveAspectRatio="none" className="h-7 w-full">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" opacity="0.8" />
    </svg>
  );
}

export function WatchlistSidebar({
  watchlist, selectedTicker, onSelect, collapsed, onToggle, loading,
}: WatchlistSidebarProps) {
  const [query, setQuery] = useState("");

  const filtered = query
    ? watchlist.filter((t) => t.ticker.replace(".JK", "").toLowerCase().includes(query.toLowerCase()))
    : watchlist;

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-border bg-card/30 transition-all duration-200",
        collapsed ? "w-12" : "w-64",
      )}
    >
      <div className={cn("flex items-center justify-between border-b border-border px-2 py-2",
        collapsed && "justify-center")}>
        {!collapsed && (
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
            Watchlist
          </span>
        )}
        <button onClick={onToggle} type="button" aria-label="Toggle sidebar"
          className="rounded-lg border border-border p-1.5 text-muted-foreground hover:text-foreground">
          {collapsed ? <ChevronsRight className="size-3.5" /> : <ChevronsLeft className="size-3.5" />}
        </button>
      </div>

      {!collapsed && (
        <div className="px-2 py-2">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-secondary/40 px-2">
            <Search className="size-3 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Cari ticker…"
              className="w-full bg-transparent py-1.5 text-xs font-mono text-foreground placeholder:text-muted-foreground focus:outline-none"
            />
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1">
        {loading && watchlist.length === 0 ? (
          <div className="space-y-1.5 p-1">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg bg-secondary/40" />
            ))}
          </div>
        ) : collapsed ? (
          filtered.map((t) => {
            const sym = t.ticker.replace(".JK", "");
            const isUp = (t.price_change_pct ?? 0) >= 0;
            return (
              <button key={t.ticker} onClick={() => onSelect(t.ticker)} type="button"
                title={sym}
                className={cn(
                  "flex h-9 w-full items-center justify-center gap-1.5 rounded-lg border border-transparent transition-colors",
                  selectedTicker === t.ticker
                    ? "border-chart-2/40 bg-chart-2/[0.08]"
                    : "hover:bg-secondary/40",
                )}>
                <span className={cn("size-1.5 rounded-full", isUp ? "bg-chart-2" : "bg-destructive")} />
              </button>
            );
          })
        ) : (
          filtered.map((t) => {
            const sym = t.ticker.replace(".JK", "");
            const isUp = (t.price_change_pct ?? 0) >= 0;
            const series = (t.price_series ?? [])
              .map((p) => (p.close != null ? p.close : null))
              .filter((v): v is number => v != null)
              .slice(-30);
            return (
              <button key={t.ticker} onClick={() => onSelect(t.ticker)} type="button"
                className={cn(
                  "w-full rounded-xl p-3 text-left transition-all duration-200 ring-1",
                  selectedTicker === t.ticker
                    ? "ring-chart-2/60 bg-chart-2/[0.08]"
                    : "ring-foreground/10 bg-card hover:ring-foreground/20 hover:bg-secondary/40",
                )}>
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-foreground text-xs tracking-wide uppercase">{sym}</span>
                  {t.rsi14 != null && (
                    <span className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider",
                      t.rsi14 > 70 ? "text-destructive bg-destructive/10 border border-destructive/20"
                        : t.rsi14 < 30 ? "text-chart-2 bg-chart-2/10 border border-chart-2/20"
                        : "text-muted-foreground bg-secondary border border-border")}>
                      {t.rsi14 > 70 ? "OB" : t.rsi14 < 30 ? "OS" : "—"}
                    </span>
                  )}
                </div>
                <div className="mt-1.5 font-mono text-sm font-semibold text-foreground tabular-nums">
                  {t.last_close != null ? `Rp ${t.last_close.toLocaleString("id-ID")}` : "—"}
                </div>
                <div className={cn("font-mono text-[11px] mt-0.5 flex items-center gap-1",
                  isUp ? "text-chart-2" : "text-destructive")}>
                  <span>{isUp ? "▲" : "▼"}</span>
                  <span>{t.price_change_pct != null ? `${isUp ? "+" : ""}${t.price_change_pct.toFixed(2)}%` : "—"}</span>
                </div>
                {series.length >= 2 && <SparklineMini series={series} isUp={isUp} />}
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}