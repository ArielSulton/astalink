import type { JourneySectionState } from "@/lib/api-client";

type SectionStateProps = {
  state: JourneySectionState;
  message?: string | null;
  timestamp?: string | null;
  onRetry?: () => void;
  children: React.ReactNode;
};

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function SectionState({
  state,
  message,
  timestamp,
  onRetry,
  children,
}: SectionStateProps) {
  if (state === "error") {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          {message || "Bagian ini belum dapat diperbarui."}
        </p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="min-h-11 rounded-lg border border-border px-3 text-sm font-semibold text-foreground hover:bg-secondary"
          >
            Coba lagi
          </button>
        )}
      </div>
    );
  }

  if (state === "empty") {
    return (
      <p className="text-sm text-muted-foreground">
        Belum ada data untuk ditampilkan.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {children}
      {state === "stale" && (
        <p className="text-xs text-muted-foreground">
          Data perlu diperbarui
          {timestamp ? ` · ${formatTimestamp(timestamp)}` : ""}.
        </p>
      )}
    </div>
  );
}
