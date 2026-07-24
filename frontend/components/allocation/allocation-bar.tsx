import { cn } from "@/lib/utils";

// The hero element of View 1 — the allocation IS the answer.
const SEGMENTS = [
  { key: "cash" as const, label: "Kas", color: "bg-slate-500" },
  { key: "stocks" as const, label: "Saham", color: "bg-sky-500" },
  { key: "business" as const, label: "Bisnis", color: "bg-emerald-500" },
];

interface AllocationBarProps {
  allocation: { cash: number; stocks: number; business: number };
  className?: string;
}

export function AllocationBar({ allocation, className }: AllocationBarProps) {
  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex h-14 w-full overflow-hidden rounded-lg border border-border">
        {SEGMENTS.map(({ key, label, color }) => {
          const pct = allocation[key];
          if (pct <= 0) return null;
          return (
            <div
              key={key}
              style={{ width: `${pct * 100}%` }}
              className={cn(color, "flex items-center justify-center transition-all")}
            >
              {pct >= 0.08 && (
                <span className="text-[11px] font-bold font-mono text-white drop-shadow">
                  {label} {(pct * 100).toFixed(0)}%
                </span>
              )}
            </div>
          );
        })}
      </div>
      <div className="flex gap-4 flex-wrap">
        {SEGMENTS.map(({ key, label, color }) => (
          <div key={key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className={cn("h-2.5 w-2.5 rounded-sm", color)} />
            {label}: <span className="font-mono font-bold text-foreground">{(allocation[key] * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
