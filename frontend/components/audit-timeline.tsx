import { cn } from "@/lib/utils";

interface TimelineEvent {
  ts: string;
  node: string;
  status: string;
  variant?: "default" | "success" | "error";
}

export function AuditTimeline({ events }: { events: TimelineEvent[] }) {
  const dotColor: Record<string, string> = {
    default: "bg-blue-500",
    success: "bg-green-500",
    error: "bg-red-500",
  };

  return (
    <ol className="border-l-2 border-gray-200 pl-4 space-y-4">
      {events.map((e, i) => (
        <li key={i} className="relative">
          <span
            className={cn(
              "absolute -left-[9px] top-1 w-3 h-3 rounded-full",
              dotColor[e.variant ?? "default"],
            )}
          />
          <div className="text-xs text-muted-foreground">
            {new Date(e.ts).toLocaleString("id-ID")}
          </div>
          <div className="font-medium text-sm">{e.node}</div>
          <div className="text-sm text-muted-foreground">{e.status}</div>
        </li>
      ))}
    </ol>
  );
}
