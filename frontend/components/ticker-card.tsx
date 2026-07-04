"use client";

interface TickerCardProps {
  ticker: string;
  lastClose: number | null;
  priceChangePct: number | null;
  rsi14: number | null;
  series?: (number | null)[] | null;
  selected?: boolean;
  onClick: () => void;
}

function Sparkline({ series, isUp }: { series: number[]; isUp: boolean }) {
  const min = Math.min(...series);
  const max = Math.max(...series);
  const range = max - min || 1;
  const points = series
    .map((v, i) => {
      const x = (i / (series.length - 1)) * 100;
      const y = 26 - ((v - min) / range) * 22;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const color = isUp ? "#4ade80" : "#f87171";
  const gradId = `spark-${isUp ? "up" : "down"}`;

  return (
    <svg viewBox="0 0 100 28" preserveAspectRatio="none" className="w-full h-7 mt-2.5">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.22" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,28 ${points} 100,28`} fill={`url(#${gradId})`} />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
        opacity="0.85"
      />
    </svg>
  );
}

export function TickerCard({
  ticker,
  lastClose,
  priceChangePct,
  rsi14,
  series,
  selected = false,
  onClick,
}: TickerCardProps) {
  const symbol = ticker.replace(".JK", "");
  const isUp = (priceChangePct ?? 0) >= 0;
  const rsiLabel =
    rsi14 != null ? (rsi14 > 70 ? "OB" : rsi14 < 30 ? "OS" : null) : null;

  const badgeClass =
    rsiLabel === "OB"
      ? "text-rose-400 bg-rose-500/10 border border-rose-500/20"
      : rsiLabel === "OS"
      ? "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20"
      : "text-muted-foreground bg-secondary border border-border";

  const sparkSeries = (series ?? []).filter((v): v is number => v != null).slice(-30);

  return (
    <button
      onClick={onClick}
      type="button"
      className={`rounded-2xl p-4 pb-3 text-left w-full transition-all duration-200 border ${
        selected
          ? "border-chart-2/60 bg-chart-2/[0.08] shadow-[0_8px_24px_-8px_rgba(0,0,0,0.45)] ring-1 ring-chart-2/20"
          : "border-border bg-card hover:border-border/80 hover:bg-secondary/40"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="font-mono font-bold text-foreground text-xs tracking-wide uppercase">{symbol}</span>
        {rsiLabel && (
          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${badgeClass}`}>
            {rsiLabel}
          </span>
        )}
      </div>
      <div className="mt-2 font-mono text-lg font-semibold text-foreground leading-none tracking-tight">
        {lastClose != null ? (
          `Rp ${lastClose.toLocaleString("id-ID")}`
        ) : (
          <span className="text-muted-foreground font-normal">—</span>
        )}
      </div>
      <div
        className="font-mono text-xs mt-1.5 flex items-center gap-1 font-medium"
        style={{ color: isUp ? "#4ade80" : "#f87171" }}
      >
        <span>{isUp ? "▲" : "▼"}</span>
        <span>
          {priceChangePct != null
            ? `${isUp ? "+" : ""}${priceChangePct.toFixed(2)}%`
            : "—"}
        </span>
      </div>
      {sparkSeries.length >= 2 && <Sparkline series={sparkSeries} isUp={isUp} />}
    </button>
  );
}
