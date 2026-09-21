import Link from "next/link";

import type { JourneyHomeResponse } from "@/lib/api-client";

import { SectionState } from "./section-state";

const STATUS_LABELS: Record<
  JourneyHomeResponse["readiness_summary"]["status"],
  string
> = {
  ready: "Siap",
  needs_input: "Perlu dilengkapi",
  not_ready: "Belum siap",
  unavailable: "Belum tersedia",
};

const GAP_LABELS: Record<string, string> = {
  "current_state.stage": "Tahap dan pendapatan bisnis",
  "capital_need.breakdown": "Rincian kebutuhan modal",
  "deal_structure.instrument": "Bentuk imbalan investasi",
};

const BLOCKER_LABELS: Record<string, string> = {
  EMERGENCY_FUND: "Dana darurat belum memadai",
  BORROWED_CAPITAL: "Modal investasi berasal dari pinjaman",
  SHORT_HORIZON: "Waktu kebutuhan dana terlalu dekat",
  CONCENTRATION: "Porsi pada satu aset terlalu besar",
};

export function ReadinessCard({
  summary,
  health,
  onRetry,
}: {
  summary: JourneyHomeResponse["readiness_summary"];
  health?: JourneyHomeResponse["section_health"][string];
  onRetry: () => void;
}) {
  const gaps = [
    ...summary.decisive_gaps.map(
      (gap) => GAP_LABELS[gap] ?? "Informasi kesiapan tambahan",
    ),
    ...summary.blocker_codes.map(
      (blocker) =>
        BLOCKER_LABELS[blocker] ?? "Batas keamanan perlu ditinjau",
    ),
  ];

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Kesiapan finansial
          </p>
          <h2 className="mt-1 text-lg font-bold text-foreground">
            {STATUS_LABELS[summary.status]}
          </h2>
        </div>
        <span className="rounded-full border border-border bg-secondary px-2.5 py-1 text-xs font-semibold text-foreground">
          {gaps.length} catatan
        </span>
      </div>

      {health?.state === "error" ? (
        <div className="mt-4">
          <SectionState
            state="error"
            message={health.message}
            onRetry={onRetry}
          >
            {null}
          </SectionState>
        </div>
      ) : gaps.length > 0 ? (
        <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
          {gaps.slice(0, 3).map((gap) => (
            <li key={gap} className="flex gap-2">
              <span aria-hidden="true">•</span>
              <span>{gap}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">
          Tidak ada hambatan utama yang terdeteksi.
        </p>
      )}

      {health?.state !== "error" && (
        <Link
          href={summary.continuation_href}
          className="mt-4 inline-flex min-h-11 items-center text-sm font-semibold text-primary"
        >
          Lihat kesiapan
        </Link>
      )}
    </section>
  );
}
