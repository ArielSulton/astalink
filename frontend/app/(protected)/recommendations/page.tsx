"use client";
import { useCallback, useEffect, useState } from "react";
import { Sparkles, TrendingUp } from "lucide-react";
import { toast } from "sonner";
import { api, type RecommendationsResponse, type RecommendationItem } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { useWorkspace } from "@/components/workspace-context";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { StockVerdictCard } from "@/components/allocation/stock-verdict-card";

const TOP_N = 8;

function reasonChips(item: RecommendationItem): string[] {
  const chips: string[] = [];
  if (item.content_score >= 50) chips.push("Tren teknikal positif");
  if (item.user_score >= 50) chips.push("Cocok dengan profil portofolio Anda");
  if (chips.length === 0) chips.push("Skor gabungan tertinggi di antara kandidat yang tersedia");
  return chips;
}

export default function RecommendationsPage() {
  const { workspaceId } = useWorkspace();
  const [data, setData] = useState<RecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!workspaceId) {
      setData(null);
      return;
    }
    setLoading(true);
    setData(null);
    try {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      const res = await api.getRecommendations(workspaceId, session.access_token);
      setData(res);
    } catch {
      toast.error("Gagal memuat rekomendasi saham.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const topItems = data?.items.slice(0, TOP_N) ?? [];
  const restItems = data?.items.slice(TOP_N) ?? [];

  return (
    <div className="p-8 space-y-6 max-w-6xl w-full mx-auto bg-background min-h-screen text-foreground">
      <PageHeader
        eyebrow="AI Rekomendasi"
        title="Saham Layak Dibeli"
        className="border-b border-border pb-5"
      />

      {!workspaceId && (
        <EmptyState icon={Sparkles} title="Pilih Workspace">
          Pilih workspace di kanan atas untuk melihat rekomendasi saham Anda.
        </EmptyState>
      )}

      {workspaceId && loading && !data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-56 rounded-xl bg-card animate-pulse ring-1 ring-foreground/10" />
          ))}
        </div>
      )}

      {workspaceId && data && (
        <>
          {!data.personalized && data.fallback_reason && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-4 py-3">
              <p className="text-xs text-amber-400 font-mono">{data.fallback_reason}</p>
            </div>
          )}

          {topItems.length === 0 ? (
            <EmptyState icon={TrendingUp} title="Belum Ada Rekomendasi">
              Data pasar untuk universe saham belum tersedia. Coba muat ulang beberapa saat lagi.
            </EmptyState>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {topItems.map((item) => (
                <div key={item.ticker} className="space-y-2">
                  <div className="flex items-center justify-between px-1">
                    <span className="text-[10px] font-mono font-bold text-muted-foreground uppercase tracking-wider">
                      #{item.rank} · Skor Hybrid {item.hybrid_score.toFixed(0)}/100
                    </span>
                  </div>
                  <ul className="px-1 text-xs text-muted-foreground space-y-0.5">
                    {reasonChips(item).map((c) => (
                      <li key={c}>✓ {c}</li>
                    ))}
                  </ul>
                  {item.verdict ? (
                    <StockVerdictCard verdict={item.verdict} />
                  ) : (
                    <div className="rounded-xl border border-border bg-card px-4 py-6 text-center text-xs text-muted-foreground">
                      Verdict lengkap untuk {item.ticker} belum tersedia.
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {restItems.length > 0 && (
            <div className="rounded-xl bg-card overflow-hidden ring-1 ring-foreground/10">
              <div className="px-5 py-4 border-b border-border">
                <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
                  Kandidat Lainnya
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-secondary/40 text-left text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
                      <th className="px-5 py-3">Peringkat</th>
                      <th className="px-4 py-3">Saham</th>
                      <th className="px-4 py-3">Sektor</th>
                      <th className="px-4 py-3 text-right">Skor Hybrid</th>
                    </tr>
                  </thead>
                  <tbody>
                    {restItems.map((item) => (
                      <tr key={item.ticker} className="border-b border-border/60 last:border-0 hover:bg-secondary/20 transition-colors">
                        <td className="px-5 py-3 font-mono text-muted-foreground">#{item.rank}</td>
                        <td className="px-4 py-3 font-mono font-bold">{item.ticker}</td>
                        <td className="px-4 py-3 text-muted-foreground">{item.sector}</td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums font-semibold">
                          {item.hybrid_score.toFixed(0)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <p className="text-[10px] text-muted-foreground/70 font-mono">
            Rekomendasi ini dihasilkan otomatis dari data pasar dan portofolio Anda, bukan nasihat investasi resmi.
          </p>
        </>
      )}
    </div>
  );
}
