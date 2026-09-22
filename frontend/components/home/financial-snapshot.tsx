import type {
  JourneyFinancialMetric,
  JourneyHomeResponse,
} from "@/lib/api-client";

import { SectionState } from "./section-state";

type FinancialSnapshotProps = {
  metrics: JourneyFinancialMetric[];
  sectionHealth: JourneyHomeResponse["section_health"];
  onRetry: () => void;
};

function formatIdr(value: number): string {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(value);
}

function sourceSection(metric: JourneyFinancialMetric): string {
  if (metric.source === "business_financial_records") return "business";
  return metric.source;
}

export function FinancialSnapshot({
  metrics,
  sectionHealth,
  onRetry,
}: FinancialSnapshotProps) {
  return (
    <section aria-labelledby="financial-snapshot-title">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 id="financial-snapshot-title" className="text-base font-bold">
          Ringkasan keuangan
        </h2>
        <span className="text-xs text-muted-foreground">
          Nilai yang didukung data terbaru
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((metric) => {
          const health = sectionHealth[sourceSection(metric)];
          return (
            <article
              key={metric.key}
              className="rounded-xl border border-border bg-card p-4"
            >
              <p className="mb-2 text-xs font-semibold text-muted-foreground">
                {metric.label}
              </p>
              <SectionState
                state={metric.state}
                message={health?.message}
                timestamp={metric.as_of}
                onRetry={metric.state === "error" ? onRetry : undefined}
              >
                {metric.value === null ? (
                  <p className="text-sm text-muted-foreground">
                    Nilai belum tersedia.
                  </p>
                ) : (
                  <p className="font-mono text-xl font-bold tabular-nums text-foreground">
                    {formatIdr(metric.value)}
                  </p>
                )}
                {metric.change_text && (
                  <p className="text-xs text-muted-foreground">
                    {metric.change_text}
                  </p>
                )}
              </SectionState>
            </article>
          );
        })}
      </div>
    </section>
  );
}
