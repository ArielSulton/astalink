import Link from "next/link";

import type { JourneyHomeResponse } from "@/lib/api-client";

import { SectionState } from "./section-state";

export function PendingApprovalsCard({
  count,
  href,
  health,
  onRetry,
}: {
  count: number;
  href: string;
  health?: JourneyHomeResponse["section_health"][string];
  onRetry: () => void;
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
        Persetujuan
      </p>
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
      ) : (
      <div className="mt-1 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            {count > 0 ? `${count} menunggu tindakan` : "Tidak ada yang tertunda"}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {count > 0
              ? "Tinjau keputusan sebelum dilanjutkan."
              : "Semua permintaan sudah tertangani."}
          </p>
        </div>
        <Link
          href={href}
          className="inline-flex min-h-11 shrink-0 items-center text-sm font-semibold text-primary"
        >
          Lihat
        </Link>
      </div>
      )}
    </section>
  );
}
