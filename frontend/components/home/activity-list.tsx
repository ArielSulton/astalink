import Link from "next/link";

import type { JourneyHomeResponse } from "@/lib/api-client";

import { SectionState } from "./section-state";

function formatAmount(value: number): string {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function ActivityList({
  items,
  health,
  onRetry,
}: {
  items: JourneyHomeResponse["recent_activity"];
  health?: JourneyHomeResponse["section_health"][string];
  onRetry: () => void;
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-lg font-bold text-foreground">Aktivitas terbaru</h2>
      {health?.state === "error" ? (
        <div className="mt-3">
          <SectionState
            state="error"
            message={health.message}
            onRetry={onRetry}
          >
            {null}
          </SectionState>
        </div>
      ) : items.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">
          Belum ada aktivitas terbaru.
        </p>
      ) : (
        <ul className="mt-3 divide-y divide-border">
          {items.map((item) => (
            <li key={`${item.kind}-${item.id}`}>
              <Link
                href={item.href}
                className="flex min-h-16 items-center justify-between gap-3 py-3"
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-foreground">
                    {item.title}
                  </span>
                  <span className="block text-xs text-muted-foreground">
                    {item.status} · {formatTime(item.occurred_at)}
                  </span>
                </span>
                {item.amount !== null && (
                  <span className="shrink-0 font-mono text-sm font-bold tabular-nums text-foreground">
                    {formatAmount(item.amount)}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
