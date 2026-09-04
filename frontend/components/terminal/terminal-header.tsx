"use client";
import { Wallet } from "lucide-react";

interface TerminalHeaderProps {
  cashBalance: number | null;
  workspaceName: string | null;
}

export function TerminalHeader({ cashBalance, workspaceName }: TerminalHeaderProps) {
  return (
    <div className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-border bg-card/50 px-4 backdrop-blur-sm">
      <div className="flex items-center gap-2.5">
        {workspaceName && (
          <span className="rounded-lg border border-border bg-secondary px-2.5 py-1 text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
            {workspaceName}
          </span>
        )}
        <span className="hidden sm:inline-flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground">
          <kbd className="rounded border border-border bg-secondary px-1.5 py-0.5 font-mono">⌘K</kbd>
          command palette
        </span>
      </div>
      {/* Hidden per concept change (2026-09) — saldo widget removed from
         dashboard header along with the Portfolio strip / /portfolio nav entry.
      {cashBalance != null && (
        <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-1.5">
          <div className="flex size-7 items-center justify-center rounded-lg bg-chart-2/10 border border-chart-2/25">
            <Wallet className="size-3.5 text-chart-2" />
          </div>
          <div className="leading-tight text-right">
            <p className="text-[9px] font-mono font-bold uppercase tracking-wider text-muted-foreground">Saldo</p>
            <p className="font-mono text-sm font-bold text-foreground tabular-nums">
              Rp {cashBalance.toLocaleString("id-ID", { maximumFractionDigits: 0 })}
            </p>
          </div>
        </div>
      )}
      */}
    </div>
  );
}