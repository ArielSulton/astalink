import Link from "next/link";

import { AllocationBar } from "@/components/allocation/allocation-bar";
import type { JourneyHomeResponse } from "@/lib/api-client";

import { SectionState } from "./section-state";

export function AllocationPreview({
  preview,
  health,
  onRetry,
}: {
  preview: JourneyHomeResponse["allocation_preview"];
  health?: JourneyHomeResponse["section_health"][string];
  onRetry: () => void;
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
        Rencana dana
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
      ) : preview ? (
        <>
          <div className="mt-2 flex items-center justify-between gap-3">
            <h2 className="text-lg font-bold text-foreground">
              Pembagian terbaru
            </h2>
            <span className="rounded-full border border-border bg-secondary px-2.5 py-1 text-xs font-semibold capitalize text-foreground">
              Keyakinan {preview.confidence_label}
            </span>
          </div>
          <SectionState
            state={health?.state === "stale" ? "stale" : "ready"}
            timestamp={preview.as_of}
          >
            <AllocationBar allocation={preview} className="mt-5" />
          </SectionState>
          {preview.data_gaps.length > 0 && (
            <p className="mt-4 text-xs text-muted-foreground">
              Masih ada {preview.data_gaps.length} data yang dapat dilengkapi.
            </p>
          )}
        </>
      ) : (
        <>
          <h2 className="mt-1 text-lg font-bold text-foreground">
            Belum ada pembagian dana
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Lengkapi kesiapan untuk mendapatkan gambaran pembagian yang sesuai.
          </p>
        </>
      )}
      {health?.state !== "error" && (
        <Link
          href="/allocation"
          className="mt-4 inline-flex min-h-11 items-center text-sm font-semibold text-primary"
        >
          Buka rencana dana
        </Link>
      )}
    </section>
  );
}
