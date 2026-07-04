import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  approved: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  completed: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  filled: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  positive: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  partial: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  awaiting_approval: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  pending: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  rejected: "text-rose-400 bg-rose-500/10 border-rose-500/20",
  rejected_after_max_revisions: "text-rose-400 bg-rose-500/10 border-rose-500/20",
  failed: "text-rose-400 bg-rose-500/10 border-rose-500/20",
  negative: "text-rose-400 bg-rose-500/10 border-rose-500/20",
};

const NEUTRAL = "text-muted-foreground bg-secondary border-border";

interface StatusBadgeProps {
  status: string | null | undefined;
  className?: string;
  children?: React.ReactNode;
}

export function StatusBadge({ status, className, children }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider border",
        status ? STATUS_STYLES[status] ?? NEUTRAL : NEUTRAL,
        className,
      )}
    >
      {children ?? status ?? "—"}
    </span>
  );
}
