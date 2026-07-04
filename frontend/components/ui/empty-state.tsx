import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: LucideIcon;
  title?: string;
  className?: string;
  children?: React.ReactNode;
}

export function EmptyState({ icon: Icon, title, className, children }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 px-6 gap-3 text-center bg-card border border-border rounded-2xl",
        className,
      )}
    >
      <div className="w-12 h-12 rounded-2xl bg-chart-2/10 border border-chart-2/20 flex items-center justify-center mb-1">
        <Icon className="h-6 w-6 text-chart-2" />
      </div>
      {title && <p className="text-sm font-semibold text-foreground">{title}</p>}
      {children && (
        <div className="text-xs text-muted-foreground max-w-sm leading-relaxed">{children}</div>
      )}
    </div>
  );
}
