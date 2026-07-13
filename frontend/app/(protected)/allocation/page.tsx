"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ClipboardList, Info, Lock, RefreshCw, X } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { AllocationBar } from "@/components/allocation/allocation-bar";
import { BusinessPanel, VetoPanel } from "@/components/allocation/business-panel";
import { StockVerdictCard } from "@/components/allocation/stock-verdict-card";
import { useWorkspace } from "@/components/workspace-context";
import { api, type AnalyzeResponse, type Business } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

const TIER_LABELS: Record<string, { label: string; cls: string }> = {
  insufficient: { label: "INSUFFICIENT", cls: "text-rose-400 border-rose-500/40" },
  partial: { label: "PARTIAL", cls: "text-amber-400 border-amber-500/40" },
  ok: { label: "OK", cls: "text-emerald-400 border-emerald-500/40" },
};

const CONFIDENCE_CLS: Record<string, string> = {
  LOW: "text-rose-400 border-rose-500/40",
  MEDIUM: "text-amber-400 border-amber-500/40",
  HIGH: "text-emerald-400 border-emerald-500/40",
};

async function getToken(): Promise<string | null> {
  const { data: { session } } = await createClient().auth.getSession();
  return session?.access_token ?? null;
}

export default function AllocationPage() {
  const { workspaceId } = useWorkspace();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [biasDismissed, setBiasDismissed] = useState(false);

  useEffect(() => {
    if (!workspaceId) return;
    (async () => {
      const token = await getToken();
      if (!token) return;
      try {
        setBusinesses(await api.listBusinesses(workspaceId, token));
      } catch {
        /* business list is optional for the stocks-only path */
      }
    })();
  }, [workspaceId]);

  const analyze = useCallback(async () => {
    if (!workspaceId) { toast.error("Pilih workspace terlebih dahulu."); return; }
    const token = await getToken();
    if (!token) { toast.error("Sesi berakhir, silakan login ulang."); return; }
    setLoading(true);
    setBiasDismissed(false); // the bias strip is always regenerated
    try {
      setResult(await api.analyzeAllocation(
        { workspace_id: workspaceId, ...(businessId ? { business_id: businessId } : {}) },
        token,
      ));
    } catch {
      toast.error("Analisis alokasi gagal. Coba lagi.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, businessId]);

  const layer0 = result?.layer0 ?? null;
  const tier = layer0 ? TIER_LABELS[layer0.completeness_tier] : null;

  return (
    <div className="space-y-6 p-6">
      <PageHeader eyebrow="Layer 0 — Capital Allocation" title="Alokasi Modal">
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={businessId}
            onChange={(e) => setBusinessId(e.target.value)}
            className="h-9 rounded-md border border-border bg-background px-2 text-sm"
          >
            <option value="">Tanpa bisnis (saham vs kas saja)</option>
            {businesses.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
          <Button variant="outline" render={<Link href="/allocation/investor" />}>
            Profil Investor
          </Button>
          <Button onClick={analyze} disabled={loading}>
            <RefreshCw className={cn("h-4 w-4 mr-1", loading && "animate-spin")} />
            Analisis
          </Button>
        </div>
      </PageHeader>

      {!result && !loading && (
        <EmptyState icon={ClipboardList} title="Belum ada analisis">
          Pilih bisnis (opsional) lalu jalankan analisis. Layer 0 memutuskan dulu
          apakah uang ini layak masuk saham atau bisnis sama sekali — sebelum satu
          saham pun dianalisis.
        </EmptyState>
      )}
      {loading && <Skeleton className="h-64 w-full" />}

      {/* ------------- View 4: INSUFFICIENT_DATA — a real state, not an error ------------- */}
      {layer0?.status === "insufficient_data" && (
        <Card className="border-sky-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ClipboardList className="h-5 w-5 text-sky-400" />
              Belum bisa memutuskan — dan itu jawaban yang benar
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              Kelengkapan data bisnis: <span className="font-mono font-bold text-foreground">{(layer0.completeness * 100).toFixed(0)}%</span> (di bawah ambang 40%).
              Sistem menolak mengarang alokasi dari data yang bolong. Jawab checklist ini, lalu analisis ulang.
            </p>
          </CardHeader>
          <CardContent className="space-y-2">
            {layer0.questions.map((q, i) => (
              <div key={q.field} className="flex items-start gap-3 rounded-lg border border-border px-3 py-2.5">
                <span className="font-mono text-xs font-bold text-sky-400 mt-0.5">{i + 1}</span>
                <p className="text-sm">{q.question}</p>
              </div>
            ))}
            {layer0.business_id && (
              <Button variant="outline" className="mt-2"
                render={<Link href={`/allocation/intake/${layer0.business_id}`} />}>
                Isi profil intake lengkap →
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* ------------- View 1: allocation (the answer) ------------- */}
      {layer0?.status === "allocated" && layer0.allocation && (
        <>
          {/* Bias warning strip — dismissible, but regenerated on every run */}
          {!biasDismissed && layer0.business_id && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/5 px-3 py-2.5">
              <Info className="h-4 w-4 mt-0.5 text-amber-400 shrink-0" />
              <p className="text-xs text-foreground flex-1">
                Sistem ini memegang 100% data saham dan {(layer0.completeness * 100).toFixed(0)}% data bisnis Anda.
                Kelengkapan data bukan kualitas aset. Jangan biarkan saham menang hanya karena datanya lebih rapi.
              </p>
              <button onClick={() => setBiasDismissed(true)} aria-label="Tutup">
                <X className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
              </button>
            </div>
          )}

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <CardTitle className="text-base">Alokasi yang disarankan</CardTitle>
                <div className="flex items-center gap-2">
                  <span className={cn("px-2 py-0.5 rounded border text-[10px] font-bold font-mono", CONFIDENCE_CLS[layer0.confidence_label])}>
                    KEYAKINAN: {layer0.confidence_label} ({layer0.confidence}/100)
                  </span>
                  {layer0.business_id && tier && (
                    <span className={cn("px-2 py-0.5 rounded border text-[10px] font-bold font-mono", tier.cls)}>
                      DATA BISNIS: {(layer0.completeness * 100).toFixed(0)}% · {tier.label}
                    </span>
                  )}
                </div>
              </div>
              {layer0.completeness_tier === "partial" && (
                <p className="text-[11px] text-amber-400">
                  Keyakinan dibatasi maksimal 50/100 karena kelengkapan data bisnis 40–70%.
                </p>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              <AllocationBar allocation={layer0.allocation} />
              <div className="flex gap-4 text-[11px] font-mono text-muted-foreground flex-wrap">
                <span>Skor bisnis: <b className={cn("text-foreground", layer0.business_score === null && "text-rose-400")}>{layer0.business_score ?? "UNKNOWN"}</b></span>
                <span>Skor saham: <b className="text-foreground">{layer0.stock_score ?? "—"}</b></span>
                <span>Baseline (obligasi/indeks): <b className="text-foreground">{layer0.baseline_score ?? "—"}</b> — selalu tersedia</span>
              </div>
            </CardContent>
          </Card>

          {/* Symmetric reasoning panels — neither side is the default */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Kenapa tidak 100% saham</CardTitle></CardHeader>
              <CardContent><p className="text-xs text-muted-foreground whitespace-pre-line">{layer0.why_not_all_stocks || "—"}</p></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Kenapa tidak 100% bisnis</CardTitle></CardHeader>
              <CardContent><p className="text-xs text-muted-foreground whitespace-pre-line">{layer0.why_not_all_business || "—"}</p></CardContent>
            </Card>
          </div>

          {/* Blocker panel — actionable to-do, not a warning */}
          {layer0.business_id && layer0.questions.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Yang harus dijawab agar porsi bisnis bisa naik</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1.5">
                {layer0.questions.slice(0, 8).map((q) => (
                  <div key={q.field} className="flex items-start gap-2 text-xs">
                    <input type="checkbox" disabled className="mt-0.5" />
                    <span>{q.question}</span>
                  </div>
                ))}
                <Button variant="outline" size="sm" className="mt-2"
                  render={<Link href={`/allocation/intake/${layer0.business_id}`} />}>
                  Lengkapi di form intake →
                </Button>
              </CardContent>
            </Card>
          )}

          {/* ------------- View 2 drill-down ------------- */}
          {layer0.business_id ? (
            <div>
              <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-muted-foreground mb-2">
                Detail Bisnis — {layer0.business_name}
              </h2>
              <BusinessPanel layer0={layer0} />
            </div>
          ) : (
            <VetoPanel flags={layer0.veto_flags} />
          )}

          {/* ------------- View 3: stock detail — gated by Layer 0 ------------- */}
          <div>
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-muted-foreground mb-2">
              Layer 1 — Stock Engine
            </h2>
            {layer0.allocation.stocks === 0 || !result?.stock_engine ? (
              <Card className="border-dashed opacity-80">
                <CardContent className="flex items-center gap-3 py-6">
                  <Lock className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Analisis saham tidak dijalankan</p>
                    <p className="text-xs text-muted-foreground">
                      {layer0.allocation.stocks === 0
                        ? "Layer 0 mengalokasikan 0% ke saham — tidak ada rekomendasi saham untuk dijelajahi, itu memang keputusannya."
                        : "Mesin saham tidak mengembalikan hasil."}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {result.stock_engine.macro?.detail?.length > 0 && (
                  <p className="text-[11px] font-mono text-muted-foreground">
                    Makro: {result.stock_engine.macro.detail.join(" · ")}
                    {result.stock_engine.macro.score !== null &&
                      ` (skor ${result.stock_engine.macro.score.toFixed(0)}/100)`}
                  </p>
                )}
                <div className="grid gap-4 md:grid-cols-2">
                  {Object.values(result.stock_engine.verdicts).map((v) => (
                    <StockVerdictCard key={v.ticker} verdict={v} />
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      <p className="text-[10px] text-muted-foreground border-t border-border pt-3">
        AstaLink adalah alat riset, bukan nasihat investasi. Keputusan dan risikonya milik Anda.
        Semua bobot & ambang adalah placeholder yang belum terkalibrasi backtest.
      </p>
    </div>
  );
}
