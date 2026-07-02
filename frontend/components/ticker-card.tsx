"use client";

interface TickerCardProps {
  ticker: string;
  lastClose: number | null;
  priceChangePct: number | null;
  rsi14: number | null;
  selected?: boolean;
  onClick: () => void;
}

export function TickerCard({
  ticker,
  lastClose,
  priceChangePct,
  rsi14,
  selected = false,
  onClick,
}: TickerCardProps) {
  const symbol = ticker.replace(".JK", "");
  const isUp = (priceChangePct ?? 0) >= 0;
  const rsiLabel =
    rsi14 != null ? (rsi14 > 70 ? "OB" : rsi14 < 30 ? "OS" : null) : null;

  const badgeClass =
    rsiLabel === "OB"
      ? "text-red-400 bg-red-500/10 border border-red-500/15"
      : rsiLabel === "OS"
      ? "text-emerald-400 bg-emerald-500/10 border border-emerald-500/15"
      : "text-muted-foreground bg-secondary border border-border";

  return (
    <button
      onClick={onClick}
      type="button"
      className={`rounded-2xl p-4 text-left w-full transition-all duration-200 border ${
        selected
          ? "border-primary/60 bg-primary/[0.08] shadow-[0_8px_24px_-6px_rgba(37,99,235,0.2)] ring-1 ring-primary/20"
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
        style={{ color: isUp ? "#10b981" : "#ef4444" }}
      >
        <span>{isUp ? "▲" : "▼"}</span>
        <span>
          {priceChangePct != null
            ? `${isUp ? "+" : ""}${priceChangePct.toFixed(2)}%`
            : "—"}
        </span>
      </div>
    </button>
  );
}
