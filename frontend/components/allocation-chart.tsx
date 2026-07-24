"use client";

const TICKER_COLORS: Record<string, { solid: string; gradient: string }> = {
  "BBCA.JK": { solid: "#22c55e", gradient: "from-green-500 to-green-400" },
  "TLKM.JK": { solid: "#86efac", gradient: "from-green-300 to-green-200" },
  "ASII.JK": { solid: "#16a34a", gradient: "from-green-600 to-green-500" },
  "BBRI.JK": { solid: "#4ade80", gradient: "from-green-400 to-green-300" },
};

const FALLBACK_COLORS: { solid: string; gradient: string }[] = [
  { solid: "#15803d", gradient: "from-green-700 to-green-600" },
  { solid: "#bbf7d0", gradient: "from-green-200 to-green-100" },
  { solid: "#a3a3a3", gradient: "from-neutral-400 to-neutral-300" },
  { solid: "#166534", gradient: "from-green-800 to-green-700" },
];

function colorFor(ticker: string, index: number) {
  return TICKER_COLORS[ticker] ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length];
}

function fmtIdrShort(n: number): string {
  if (n >= 1e9) return `Rp ${(n / 1e9).toLocaleString("id-ID", { maximumFractionDigits: 1 })} M`;
  if (n >= 1e6) return `Rp ${(n / 1e6).toLocaleString("id-ID", { maximumFractionDigits: 1 })} jt`;
  if (n >= 1e3) return `Rp ${(n / 1e3).toLocaleString("id-ID", { maximumFractionDigits: 0 })} rb`;
  return `Rp ${n.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;
}

export function AllocationChart({
  weights,
  cash,
  totalFunds,
  compact = false,
}: {
  weights: { ticker: string; weight: number }[];
  /** IDR earmarked for the stock sleeve (plan.cash). Enables Rupiah amounts. */
  cash?: number | null;
  /** Total funds owned (workspace balance). Enables the "vs owned" ratio. */
  totalFunds?: number | null;
  compact?: boolean;
}) {
  const sumWeights = weights.reduce((sum, w) => sum + w.weight, 0);

  // Real money mode: show the ratio of invested Rupiah vs funds owned, not
  // the internal stock-sleeve percentages (which always sum to ~100%).
  const hasMoney = cash != null && totalFunds != null && totalFunds > 0;
  const investedIdr = cash != null ? sumWeights * cash : null;

  // The single scale every visual in this component must use: a leg's share of
  // the denominator the centre label reports. In money mode that denominator is
  // total funds owned, so a 9.5% sleeve draws a 9.5% ring — the ring and the
  // number can't disagree. Without money data it falls back to sleeve weights.
  const shareOf = (weight: number) =>
    (hasMoney ? (weight * cash!) / totalFunds! : weight) * 100;

  const investedPct = Math.min(100, shareOf(sumWeights));

  // Donut segments on a circumference-100 circle (r = 15.915), starting at 12 o'clock.
  let cursor = 0;
  const segments = weights.map((w, i) => {
    const pct = Math.max(0, Math.min(100 - cursor, shareOf(w.weight)));
    const seg = { ticker: w.ticker, pct, offset: 25 - cursor, color: colorFor(w.ticker, i).solid };
    cursor += pct;
    return seg;
  });

  return (
    <div className={`flex items-center gap-6 ${compact ? "flex-col" : "flex-col sm:flex-row"}`}>
      {/* Donut */}
      <div className="relative shrink-0 w-32 h-32">
        <svg viewBox="0 0 36 36" className="w-full h-full">
          <circle
            cx="18" cy="18" r="15.915"
            fill="none"
            className="stroke-secondary"
            strokeWidth="3.4"
          />
          {segments.map((s) => (
            <circle
              key={s.ticker}
              cx="18" cy="18" r="15.915"
              fill="none"
              stroke={s.color}
              strokeWidth="3.4"
              strokeLinecap="butt"
              strokeDasharray={`${s.pct} ${100 - s.pct}`}
              strokeDashoffset={s.offset}
              className="transition-all duration-700 ease-out"
            />
          ))}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono font-bold text-foreground text-lg leading-none tabular-nums">
            {investedPct.toFixed(hasMoney ? 1 : 0)}%
          </span>
          <span className="text-[9px] text-muted-foreground font-mono uppercase tracking-wider mt-1">
            {hasMoney ? "dari dana" : "Saham"}
          </span>
          {hasMoney && (
            <span className="text-[8px] text-muted-foreground/70 font-mono tabular-nums mt-0.5">
              {fmtIdrShort(investedIdr!)}
            </span>
          )}
        </div>
      </div>

      {/* Bars */}
      <ul className="space-y-2.5 flex-1 w-full min-w-0">
        {weights.map((w, i) => {
          const cleanTicker = w.ticker.replace(".JK", "");
          const { solid, gradient } = colorFor(w.ticker, i);

          return (
            <li
              key={w.ticker}
              className="flex items-center gap-4 p-3.5 bg-secondary border border-border rounded-xl hover:border-border/60 hover:bg-card transition-all duration-200"
            >
              <div className="w-16 shrink-0 flex flex-col">
                <span className="flex items-center gap-1.5 font-mono font-bold text-foreground text-sm">
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: solid }}
                  />
                  {cleanTicker}
                </span>
                <span className="text-[10px] text-muted-foreground font-mono pl-3">IDX</span>
              </div>

              <div className="flex-1 bg-background h-2.5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${gradient} transition-all duration-500 ease-out`}
                  style={{ width: `${shareOf(w.weight)}%` }}
                />
              </div>

              <div className="w-24 text-right shrink-0">
                {cash != null && (
                  <span className="block font-mono font-bold text-foreground text-sm tabular-nums">
                    {fmtIdrShort(w.weight * cash)}
                  </span>
                )}
                <span className={`font-mono tabular-nums ${cash != null ? "text-[10px] text-muted-foreground" : "text-sm font-bold text-foreground"}`}>
                  {shareOf(w.weight).toFixed(1)}%
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
