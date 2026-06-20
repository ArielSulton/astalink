"use client";
import { useEffect, useState } from "react";
import { Briefcase, TrendingUp } from "lucide-react";
import { api, ApprovalDetail } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { AllocationChart } from "@/components/allocation-chart";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";

export default function AssetsPage() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ApprovalDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) {
      setDetail(null);
      return;
    }

    setLoading(true);
    setError(null);

    (async () => {
      try {
        const sb = createClient();
        const {
          data: { session },
        } = await sb.auth.getSession();
        if (!session) return;

        const { approvals } = await api.listApprovals(workspaceId, session.access_token);
        const completed = approvals.filter((a) => a.status === "completed");
        if (!completed.length) {
          setDetail(null);
          return;
        }

        const latest = completed[completed.length - 1];
        const d = await api.getApproval(latest.audit_id, session.access_token);
        setDetail(d);
      } catch {
        setError("Gagal memuat data aset.");
      } finally {
        setLoading(false);
      }
    })();
  }, [workspaceId]);

  const weights = detail?.plan_json?.weights ?? [];
  const cash = detail?.plan_json?.cash ?? 0;
  const cashBuffer = detail?.plan_json?.cash_buffer ?? 0;
  const narration = detail?.plan_json?.narration ?? "";

  const isApproved = detail?.legal_status === "approved";
  const statusBadgeClass = isApproved
    ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/15"
    : detail?.legal_status === "partial"
    ? "text-amber-400 bg-amber-500/10 border-amber-500/15"
    : "text-rose-400 bg-rose-500/10 border-rose-500/15";

  return (
    <div className="p-8 space-y-6 max-w-4xl w-full mx-auto bg-background min-h-screen text-foreground">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 border-b border-border pb-5 flex-wrap">
        <div>
          <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em] mb-1">
            Portfolio Balance
          </p>
          <h1 className="text-foreground text-2xl font-bold tracking-tight">
            Asset View
          </h1>
        </div>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>

      {!workspaceId && (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-muted-foreground bg-card border border-border rounded-2xl p-6">
          <Briefcase className="h-10 w-10 text-primary/80" />
          <p className="text-sm font-semibold text-foreground">Pilih Workspace</p>
          <p className="text-xs text-muted-foreground text-center max-w-xs">
            Pilih workspace di kanan atas untuk melihat alokasi aset Anda.
          </p>
        </div>
      )}

      {workspaceId && loading && (
        <div className="space-y-4">
          <div className="h-56 rounded-2xl bg-card animate-pulse border border-border" />
          <div className="grid grid-cols-2 gap-4">
            <div className="h-24 rounded-2xl bg-card animate-pulse border border-border" />
            <div className="h-24 rounded-2xl bg-card animate-pulse border border-border" />
          </div>
        </div>
      )}

      {workspaceId && !loading && error && (
        <p className="text-xs text-rose-400 p-4 rounded-xl border border-rose-500/10 bg-rose-500/5">
          {error}
        </p>
      )}

      {workspaceId && !loading && !error && !detail && (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-muted-foreground bg-card border border-border rounded-2xl p-6">
          <TrendingUp className="h-10 w-10 text-primary/80" />
          <p className="text-sm font-semibold text-foreground">Belum Ada Alokasi Disetujui</p>
          <p className="text-xs text-muted-foreground text-center max-w-sm leading-relaxed">
            Belum ada alokasi yang disetujui di workspace ini.
            <br />
            Jalankan analisis dari halaman Dashboard terlebih dahulu.
          </p>
        </div>
      )}

      {workspaceId && !loading && detail && (
        <div className="space-y-5">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground font-medium">Status Dokumen:</span>
            <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold font-mono uppercase tracking-wider border ${statusBadgeClass}`}>
              {detail.legal_status ?? "—"}
            </span>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6 shadow-xl">
            <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-5 font-mono">
              Alokasi Portofolio
            </h2>
            {weights.length > 0 ? (
              <AllocationChart weights={weights} />
            ) : (
              <p className="text-sm text-muted-foreground">Tidak ada alokasi saham.</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-2xl border border-border bg-card p-5">
              <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1 font-mono">Kas</p>
              <p className="text-2xl font-bold text-foreground font-mono">
                {(cash * 100).toFixed(1)}%
              </p>
            </div>
            <div className="rounded-2xl border border-border bg-card p-5">
              <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1 font-mono">Buffer Kas</p>
              <p className="text-2xl font-bold text-foreground font-mono">
                {(cashBuffer * 100).toFixed(1)}%
              </p>
            </div>
          </div>

          {narration && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-xl">
              <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-4 font-mono">
                Analisis AI
              </h2>
              <p className="text-sm text-muted-foreground leading-relaxed bg-secondary border border-border rounded-xl p-4">
                {narration}
              </p>
            </div>
          )}

          {detail.plan_json?.relaxations_applied &&
            detail.plan_json.relaxations_applied.length > 0 && (
              <div className="rounded-2xl border border-border bg-card p-5">
                <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3 font-mono">Relaksasi Diterapkan</p>
                <ul className="space-y-2">
                  {detail.plan_json.relaxations_applied.map((r, i) => (
                    <li key={i} className="text-xs text-muted-foreground flex items-center gap-2 font-medium">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shrink-0" />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}
        </div>
      )}
    </div>
  );
}
