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

        // Most recent completed approval
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

  return (
    <div className="p-6 space-y-5 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-white">Asset View</h1>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>

      {/* No workspace selected */}
      {!workspaceId && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-[#5b616e]">
          <Briefcase className="h-9 w-9" />
          <p className="text-sm">Pilih workspace untuk melihat alokasi aset Anda.</p>
        </div>
      )}

      {/* Loading */}
      {workspaceId && loading && (
        <div className="space-y-3">
          <div className="h-48 rounded-xl bg-[#16181c] animate-pulse border border-[#2a2d36]" />
          <div className="h-20 rounded-xl bg-[#16181c] animate-pulse border border-[#2a2d36]" />
        </div>
      )}

      {/* Error */}
      {workspaceId && !loading && error && (
        <p className="text-sm text-[#cf202f] p-4 rounded-xl border border-[#cf202f30] bg-[#cf202f08]">
          {error}
        </p>
      )}

      {/* No data */}
      {workspaceId && !loading && !error && !detail && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-[#5b616e]">
          <TrendingUp className="h-9 w-9" />
          <p className="text-sm">Belum ada alokasi yang disetujui di workspace ini.</p>
          <p className="text-xs text-[#3a3d46]">Jalankan analisis dari halaman Dashboard terlebih dahulu.</p>
        </div>
      )}

      {/* Portfolio content */}
      {workspaceId && !loading && detail && (
        <div className="space-y-4">
          {/* Legal status badge */}
          <div className="flex items-center gap-2">
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${
                detail.legal_status === "approved"
                  ? "text-[#05b169] bg-[#05b16915] border-[#05b16930]"
                  : detail.legal_status === "partial"
                  ? "text-[#f4b000] bg-[#f4b00015] border-[#f4b00030]"
                  : "text-[#cf202f] bg-[#cf202f15] border-[#cf202f30]"
              }`}
            >
              Legal: {detail.legal_status ?? "—"}
            </span>
          </div>

          {/* Allocation chart */}
          <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-5">
            <h2 className="text-xs font-medium text-[#5b616e] uppercase tracking-wide mb-4">
              Alokasi Portofolio
            </h2>
            {weights.length > 0 ? (
              <AllocationChart weights={weights} />
            ) : (
              <p className="text-sm text-[#5b616e]">Tidak ada alokasi saham.</p>
            )}
          </div>

          {/* Cash positions */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-4">
              <p className="text-xs text-[#5b616e] mb-1">Kas</p>
              <p className="text-2xl font-semibold text-white font-mono">
                {(cash * 100).toFixed(1)}%
              </p>
            </div>
            <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-4">
              <p className="text-xs text-[#5b616e] mb-1">Buffer Kas</p>
              <p className="text-2xl font-semibold text-white font-mono">
                {(cashBuffer * 100).toFixed(1)}%
              </p>
            </div>
          </div>

          {/* AI narration */}
          {narration && (
            <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-5">
              <h2 className="text-xs font-medium text-[#5b616e] uppercase tracking-wide mb-2">
                Analisis AI
              </h2>
              <p className="text-sm text-[#a8acb3] leading-relaxed">{narration}</p>
            </div>
          )}

          {/* Relaxations */}
          {detail.plan_json?.relaxations_applied &&
            detail.plan_json.relaxations_applied.length > 0 && (
              <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-4">
                <p className="text-xs text-[#5b616e] mb-2 uppercase tracking-wide">Relaksasi Diterapkan</p>
                <ul className="space-y-1">
                  {detail.plan_json.relaxations_applied.map((r, i) => (
                    <li key={i} className="text-xs text-[#a8acb3] flex items-center gap-2">
                      <span className="h-1 w-1 rounded-full bg-[#f4b000] shrink-0" />
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
