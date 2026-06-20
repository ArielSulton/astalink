"use client";

const TICKER_GRADIENTS: Record<string, string> = {
  "BBCA.JK": "from-blue-500 to-blue-400",
  "TLKM.JK": "from-red-500 to-rose-500",
  "ASII.JK": "from-emerald-500 to-emerald-600",
  "BBRI.JK": "from-amber-500 to-yellow-500",
};

export function AllocationChart({ weights }: { weights: { ticker: string; weight: number }[] }) {
  return (
    <ul className="space-y-2.5">
      {weights.map((w) => {
        const cleanTicker = w.ticker.replace(".JK", "");
        const gradient = TICKER_GRADIENTS[w.ticker] ?? "from-indigo-500 to-purple-600";

        return (
          <li
            key={w.ticker}
            className="flex items-center gap-4 p-3.5 bg-secondary border border-border rounded-xl hover:border-border/60 hover:bg-card transition-all duration-200"
          >
            <div className="w-16 shrink-0 flex flex-col">
              <span className="font-mono font-bold text-foreground text-sm">{cleanTicker}</span>
              <span className="text-[10px] text-muted-foreground font-mono">IDX</span>
            </div>

            <div className="flex-1 bg-background h-2.5 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${gradient} transition-all duration-500 ease-out`}
                style={{ width: `${w.weight * 100}%` }}
              />
            </div>

            <span className="w-16 text-right font-mono font-bold text-foreground text-sm tabular-nums">
              {(w.weight * 100).toFixed(1)}%
            </span>
          </li>
        );
      })}
    </ul>
  );
}
