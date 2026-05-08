export function AuditTimeline({ events }: { events: { ts: string; node: string; status: string }[] }) {
  return (
    <ol className="border-l-2 border-gray-200 pl-4 space-y-3">
      {events.map((e, i) => (
        <li key={i} className="relative">
          <span className="absolute -left-[9px] top-1 w-3 h-3 bg-blue-500 rounded-full" />
          <div className="text-xs text-muted-foreground">{e.ts}</div>
          <div className="font-medium">{e.node}</div>
          <div className="text-sm">{e.status}</div>
        </li>
      ))}
    </ol>
  );
}
