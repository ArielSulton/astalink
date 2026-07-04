import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  icon?: LucideIcon;
  hint?: string;
  className?: string;
}

export function StatCard({ label, value, icon: Icon, hint, className }: StatCardProps) {
  return (
    <div className={cn("rounded-2xl border border-border bg-card p-5", className)}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
          {label}
        </p>
        {Icon && (
          <div className="w-7 h-7 rounded-lg bg-chart-2/10 border border-chart-2/20 flex items-center justify-center">
            <Icon className="h-3.5 w-3.5 text-chart-2" />
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-foreground font-mono leading-none">{value}</p>
      {hint && <p className="text-[10px] text-muted-foreground/70 font-mono mt-2">{hint}</p>}
    </div>
  );
}
