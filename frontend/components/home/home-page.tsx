"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/page-header";
import { useWorkspace } from "@/components/workspace-context";
import { api, type JourneyHomeResponse } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

import { ActivityList } from "./activity-list";
import { AllocationPreview } from "./allocation-preview";
import { FinancialSnapshot } from "./financial-snapshot";
import { NextActionCard } from "./next-action-card";
import { PendingApprovalsCard } from "./pending-approvals-card";
import { QuickActions } from "./quick-actions";
import { ReadinessCard } from "./readiness-card";

type HomeLoadState = {
  workspaceId: string;
  status: "loading" | "ready" | "error";
  data: JourneyHomeResponse | null;
};

function formatJourneyTime(value: string): string {
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function WorkspaceRequired() {
  return (
    <main className="mx-auto flex min-h-full w-full max-w-3xl items-center p-4 sm:p-6 lg:p-8">
      <section className="w-full rounded-xl border border-border bg-card p-6 text-center">
        <h1 className="text-xl font-bold text-foreground">Pilih workspace</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Gunakan pemilih di bagian atas untuk melihat ringkasan perjalananmu.
        </p>
      </section>
    </main>
  );
}

function HomeSkeleton() {
  return (
    <main
      aria-label="Memuat beranda"
      className="mx-auto min-h-full w-full max-w-7xl space-y-4 p-4 sm:p-6 lg:p-8"
    >
      <div className="h-16 animate-pulse rounded-xl bg-muted" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((item) => (
          <div key={item} className="h-28 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
      <div className="h-36 animate-pulse rounded-xl bg-muted" />
    </main>
  );
}

function HomeLoadError({ onRetry }: { onRetry: () => void }) {
  return (
    <main className="mx-auto flex min-h-full w-full max-w-3xl items-center p-4 sm:p-6 lg:p-8">
      <section className="w-full rounded-xl border border-border bg-card p-6 text-center">
        <h1 className="text-xl font-bold text-foreground">
          Beranda belum dapat dimuat
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Periksa koneksi lalu coba lagi. Data yang tidak tersedia tidak akan
          ditampilkan sebagai nol.
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 min-h-11 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
        >
          Coba lagi
        </button>
      </section>
    </main>
  );
}

function JourneyHomeContent({
  data,
  onRetry,
}: {
  data: JourneyHomeResponse;
  onRetry: () => void;
}) {
  return (
    <main className="mx-auto min-h-full w-full max-w-7xl space-y-4 p-4 sm:p-6 lg:p-8">
      <PageHeader
        eyebrow={data.workspace_name}
        title="Selamat datang kembali"
        description={`Terakhir diperbarui ${formatJourneyTime(data.generated_at)}`}
      />
      <FinancialSnapshot
        metrics={data.financial_snapshot}
        sectionHealth={data.section_health}
        onRetry={onRetry}
      />
      <NextActionCard action={data.next_action} />
      <div className="grid gap-4 lg:grid-cols-2">
        <ReadinessCard
          summary={data.readiness_summary}
          health={data.section_health.readiness}
          onRetry={onRetry}
        />
        <AllocationPreview
          preview={data.allocation_preview}
          health={data.section_health.allocation}
          onRetry={onRetry}
        />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ActivityList
          items={data.recent_activity}
          health={data.section_health.activity}
          onRetry={onRetry}
        />
        <div className="space-y-4">
          <PendingApprovalsCard
            count={data.pending_approvals_count}
            href="/approvals"
            health={data.section_health.pending}
            onRetry={onRetry}
          />
          <QuickActions />
        </div>
      </div>
    </main>
  );
}

export function HomePage() {
  const { workspaceId } = useWorkspace();
  const [loadState, setLoadState] = useState<HomeLoadState | null>(null);
  const [retryVersion, setRetryVersion] = useState(0);

  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;

    (async () => {
      try {
        const {
          data: { session },
        } = await createClient().auth.getSession();
        if (!session) throw new Error("Missing authenticated session");
        const result = await api.getJourneyHome(
          workspaceId,
          session.access_token,
        );
        if (!cancelled) {
          setLoadState({ workspaceId, status: "ready", data: result });
        }
      } catch {
        if (!cancelled) {
          setLoadState({ workspaceId, status: "error", data: null });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [workspaceId, retryVersion]);

  if (!workspaceId) return <WorkspaceRequired />;

  const currentState =
    loadState?.workspaceId === workspaceId ? loadState : null;
  const retry = () => {
    setLoadState({ workspaceId, status: "loading", data: null });
    setRetryVersion((version) => version + 1);
  };

  if (!currentState || currentState.status === "loading") {
    return <HomeSkeleton />;
  }
  if (currentState.status === "error" || !currentState.data) {
    return <HomeLoadError onRetry={retry} />;
  }
  return <JourneyHomeContent data={currentState.data} onRetry={retry} />;
}
