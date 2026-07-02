import { cn } from "@/lib/utils";

interface TimelineEvent {
  ts: string;
  node: string;
  status: string;
  variant?: "default" | "success" | "error";
}

export function AuditTimeline({ events }: { events: TimelineEvent[] }) {
  const dotColor: Record<string, string> = {
    default: "bg-primary ring-4 ring-primary/20",
    success: "bg-emerald-500 ring-4 ring-emerald-500/20",
    error: "bg-rose-500 ring-4 ring-rose-500/20",
  };

  return (
    <ol className="border-l-2 border-border pl-6 space-y-6 relative ml-2">
      {events.map((e, i) => (
        <li key={i} className="relative">
          <span
            className={cn(
              "absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full border-2 border-background z-10 transition-all duration-300",
              dotColor[e.variant ?? "default"],
            )}
          />
          <div className="text-[10px] text-muted-foreground font-mono font-medium">
            {new Date(e.ts).toLocaleString("id-ID", {
              day: "numeric",
              month: "short",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </div>
          <div className="font-bold text-foreground text-sm mt-0.5 tracking-tight">{e.node}</div>
          <div className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{e.status}</div>
        </li>
      ))}
    </ol>
  );
}
