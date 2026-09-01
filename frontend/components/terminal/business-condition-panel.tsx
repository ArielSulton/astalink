"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Building2, Plus } from "lucide-react";
import { useWorkspace } from "@/components/workspace-context";
import { api, type Business, type BusinessValuationResponse } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { cn } from "@/lib/utils";

const TOOLTIP_STYLE = {
  background: "rgba(23, 23, 23, 0.97)",
  border: "1px solid rgba(255, 255, 255, 0.1)",
  color: "#fafafa",
  borderRadius: "12px",
  fontSize: "11px",
};

function fmtIDR(v: number): string {
  if (v >= 1_000_000_000_000) return `Rp ${(v / 1_000_000_000_000).toFixed(2)} T`;
  if (v >= 1_000_000_000) return `Rp ${(v / 1_000_000_000).toFixed(2)} M`;
  if (v >= 1_000_000) return `Rp ${(v / 1_000_000).toFixed(2)} Jt`;
  return `Rp ${v.toLocaleString("id-ID")}`;
}

export function BusinessConditionPanel() {
  const { workspaceId } = useWorkspace();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [valuation, setValuation] = useState<BusinessValuationResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // 1. Load businesses for the workspace.
  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;
    (async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      try {
        const list = await api.listBusinesses(workspaceId, session.access_token);
        if (cancelled) return;
        setBusinesses(list);
        if (list.length === 1) setSelectedId(list[0].id);
        else if (list.length > 0) setSelectedId(list[0].id); // default to first
        setLoading(false);
      } catch {
        if (!cancelled) { setLoading(false); setBusinesses([]); }
      }
    })();
    return () => { cancelled = true; };
  }, [workspaceId]);

  // 2. When a business is selected, fetch its valuation.
  useEffect(() => {
    if (!selectedId) { setValuation(null); return; }
    let cancelled = false;
    setValuation(null);
    (async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      try {
        const v = await api.getBusinessValuation(selectedId, session.access_token);
        if (!cancelled) setValuation(v);
      } catch {
        if (!cancelled) setValuation(null);
      }
    })();
    return () => { cancelled = true; };
  }, [selectedId]);

  // Loading state
  if (loading) {
    return (
      <div className="px-6 py-5">
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  // Empty state (no businesses)
  if (businesses.length === 0) {
    return (
      <div className="px-6 py-5">
        <Card className="border-dashed border-border bg-card/30">
          <CardContent className="py-10 text-center">
            <Building2 className="mx-auto mb-3 text-muted-foreground" size={36} />
            <p className="text-sm font-semibold text-foreground">Belum ada bisnis terdaftar</p>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              Tambahkan bisnis Anda untuk melihat valuasi DCF otomatis berdasarkan kondisi saat ini.
            </p>
            <Button render={<Link href="/business" />} variant="outline" size="sm" className="mt-5">
              <Plus className="mr-1 h-3 w-3" /> Tambah Bisnis
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Valuation card (with optional selector when multiple businesses)
  const cashData = (valuation?.financial_records ?? [])
    .map((r) => ({ year: String(r.period_year), profit: r.profit }));

  return (
    <div className="px-6 py-5">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <p className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-muted-foreground">
              Kondisi Bisnis Saat Ini
            </p>
            <p className="mt-0.5 text-sm font-semibold text-foreground">
              {valuation?.business.name ?? "Muat valuasi…"}
            </p>
          </div>
          {businesses.length > 1 && (
            <select
              value={selectedId ?? ""}
              onChange={(e) => setSelectedId(e.target.value)}
              className="h-9 w-48 rounded-lg border border-border bg-background px-2.5 text-xs font-mono text-foreground focus:outline-none"
            >
              {businesses.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          )}
        </CardHeader>

        <CardContent>
          {!valuation ? (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {/* Enterprise Value */}
              <div className="rounded-xl border border-border bg-card px-4 py-3">
                <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
                  Enterprise Value (DCF)
                </p>
                <p className="font-mono text-xl font-bold text-foreground tabular-nums">
                  {fmtIDR(valuation.valuation.enterprise_value)}
                </p>
              </div>

              {/* Key assumptions */}
              <div className="rounded-xl border border-border bg-card px-4 py-3">
                <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
                  Asumsi
                </p>
                <div className="space-y-1 text-xs text-foreground">
                  <p className="flex justify-between"><span className="text-muted-foreground">Discount rate</span>
                    <span className="font-mono">{(valuation.valuation.discount_rate * 100).toFixed(0)}%</span></p>
                  <p className="flex justify-between"><span className="text-muted-foreground">Terminal growth</span>
                    <span className="font-mono">{(valuation.valuation.terminal_growth * 100).toFixed(0)}%</span></p>
                  <p className="flex justify-between"><span className="text-muted-foreground">Tahun data</span>
                    <span className="font-mono">{valuation.valuation.projection_years}</span></p>
                </div>
              </div>

              {/* Cashflow trend */}
              <div className="rounded-xl border border-border bg-card px-4 py-3">
                <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
                  Tren Arus Kas
                </p>
                {cashData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={90}>
                    <BarChart data={cashData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                      <XAxis dataKey="year" hide />
                      <YAxis hide />
                      <Tooltip contentStyle={TOOLTIP_STYLE} />
                      <Bar dataKey="profit" fill="var(--color-chart-2)" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-xs text-muted-foreground">Tidak ada data laba.</p>
                )}
              </div>
            </div>
          )}

          {valuation?.valuation.narration && (
            <p className="mt-3 text-xs text-muted-foreground leading-relaxed">
              {valuation.valuation.narration}
            </p>
          )}
        </CardContent>

        <CardFooter className="justify-between border-t border-border pt-3">
          <span className="text-[10px] font-mono text-muted-foreground">
            DCF: {(valuation?.valuation.discount_rate ?? 0.1) * 100}% discount, {(valuation?.valuation.terminal_growth ?? 0.03) * 100}% terminal
          </span>
          <Button render={<Link href="/business" />} variant="ghost" size="sm">
            Lihat Analisis Lengkap <ArrowRight className="ml-1 h-3 w-3" />
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}