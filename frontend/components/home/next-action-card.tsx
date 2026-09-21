import { ArrowRight } from "lucide-react";
import Link from "next/link";

import type { JourneyHomeResponse } from "@/lib/api-client";

export function NextActionCard({
  action,
}: {
  action: JourneyHomeResponse["next_action"];
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-5 sm:p-6">
      <p className="mb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
        Langkah berikutnya
      </p>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-2xl">
          <h2 className="text-xl font-bold text-foreground">{action.title}</h2>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            {action.rationale}
          </p>
        </div>
        <Link
          href={action.href}
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
        >
          Lanjutkan
          <ArrowRight className="size-4" />
        </Link>
      </div>
    </section>
  );
}
