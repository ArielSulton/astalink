"use client";

import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface IntakeSectionHeaderProps {
  label: string;
  icon: LucideIcon;
  completed: number;
  total: number;
  isOpen: boolean;
}

function StatusBadge({ completed, total }: { completed: number; total: number }) {
  if (completed === total) {
    return (
      <span className="flex items-center gap-1 text-[10px] font-mono font-bold text-chart-2">
        <span className="w-4 h-4 rounded-full bg-chart-2/15 border border-chart-2/30 flex items-center justify-center">
          <svg className="w-2.5 h-2.5" viewBox="0 0 12 12" fill="none">
            <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        {completed}/{total}
      </span>
    );
  }

  if (completed > 0) {
    return (
      <span className="text-[10px] font-mono font-bold text-amber-400">
        {completed}/{total}
      </span>
    );
  }

  return (
    <span className="text-[10px] font-mono font-bold text-muted-foreground/50">
      {completed}/{total}
    </span>
  );
}

export function IntakeSectionHeader({ label, icon: Icon, completed, total, isOpen }: IntakeSectionHeaderProps) {
  return (
    <div className="flex items-center gap-2.5 flex-1 min-w-0">
      <div className={cn(
        "w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors",
        completed === total && total > 0
          ? "bg-chart-2/10 border border-chart-2/20"
          : "bg-secondary border border-border"
      )}>
        <Icon className={cn(
          "h-3.5 w-3.5",
          completed === total && total > 0 ? "text-chart-2" : "text-muted-foreground"
        )} />
      </div>
      <span className="text-sm font-medium text-foreground truncate">{label}</span>
      <div className="ml-auto flex items-center gap-2 shrink-0">
        <StatusBadge completed={completed} total={total} />
        <svg
          className={cn(
            "h-4 w-4 text-muted-foreground transition-transform duration-200 shrink-0",
            isOpen && "rotate-180"
          )}
          viewBox="0 0 16 16" fill="none"
        >
          <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  );
}
