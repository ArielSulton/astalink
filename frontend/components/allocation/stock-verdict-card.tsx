"use client";

import { AlertTriangle, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { StockVerdict } from "@/lib/api-client";

const BAND_STYLES: Record<StockVerdict["band"], { label: string; cls: string }> = {
  strong_buy: { label: "STRONG BUY", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" },
  buy: { label: "BUY", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" },
  watchlist: { label: "WATCHLIST", cls: "text-amber-400 bg-amber-500/10 border-amber-500/30" },
  avoid: { label: "AVOID", cls: "text-rose-400 bg-rose-500/10 border-rose-500/30" },
  reject: { label: "REJECT", cls: "text-rose-400 bg-rose-500/20 border-rose-500/50" },
  no_verdict: { label: "NO VERDICT", cls: "text-muted-foreground bg-secondary border-border border-dashed" },
};

// A gate is not a score — render it as a distinct PASS/FAIL/CONDITIONAL chip.
const GATE_STYLES: Record<string, string> = {
  pass: "text-emerald-400 border-emerald-500/40",
  fail: "text-rose-400 border-rose-500/40",
  conditional: "text-amber-400 border-amber-500/40",
};

const COMPONENT_LABELS: Record<string, string> = {
  a1_news: "A1 · News & Sentiment",
  a2_macro: "A2 · Makro & Regulasi",
  a3_quality: "A3 · Liquidity Gate",
  a4_flow: "A4 · Smart Money / Flow",
};

export function StockVerdictCard({ verdict }: { verdict: StockVerdict }) {
  const band = BAND_STYLES[verdict.band];
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <CardTitle className="font-mono text-lg">{verdict.ticker}</CardTitle>
          <div className="flex items-center gap-2">
            {verdict.manipulation_risk !== "low" && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold font-mono border text-rose-400 bg-rose-500/15 border-rose-500/40">
                <AlertTriangle className="h-3 w-3" />
                MANIPULASI: {verdict.manipulation_risk.toUpperCase()}
              </span>
            )}
            <span className={cn("px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono border", band.cls)}>
              {band.label}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>
            Skor: <span className="font-mono font-bold text-foreground">{verdict.score ?? "—"}</span>/100
          </span>
          <span>Horizon: {verdict.horizon || "—"}</span>
          <span
            className={cn(
              "px-1.5 py-0.5 rounded border text-[10px] font-mono font-bold",
              GATE_STYLES[verdict.gate_status] ?? "text-muted-foreground border-border",
            )}
          >
            GATE A3: {verdict.gate_status.toUpperCase()}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* A1-A4 component scores */}
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(verdict.components).map(([key, value]) => (
            <div key={key} className="rounded border border-border px-2 py-1.5">
              <p className="text-[10px] text-muted-foreground font-mono">{COMPONENT_LABELS[key] ?? key}</p>
              <p className={cn("text-sm font-mono font-bold", value === null && "text-rose-400")}>
                {value === null ? "UNKNOWN" : value.toFixed(0)}
              </p>
            </div>
          ))}
        </div>

        {/* Invalidation condition — first-class, not a footnote */}
        <div className="rounded border border-amber-500/30 bg-amber-500/5 px-3 py-2">
          <p className="text-[10px] font-black font-mono uppercase tracking-wider text-amber-400 mb-0.5">
            Kondisi pembatalan tesis
          </p>
          <p className="text-xs text-foreground">{verdict.invalidation_condition || "—"}</p>
        </div>

        {/* Evidence gaps — explicit, never hidden */}
        {verdict.evidence_gaps.length > 0 && (
          <Collapsible>
            <CollapsibleTrigger className="flex items-center gap-1 text-[11px] font-mono text-muted-foreground hover:text-foreground">
              <ChevronDown className="h-3 w-3" />
              Celah bukti ({verdict.evidence_gaps.length}) — yang TIDAK bisa diverifikasi sistem
            </CollapsibleTrigger>
            <CollapsibleContent>
              <ul className="mt-1 space-y-0.5 pl-4 list-disc text-[11px] text-muted-foreground">
                {verdict.evidence_gaps.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </CollapsibleContent>
          </Collapsible>
        )}

        {verdict.as_of && (
          <p className="text-[10px] font-mono text-muted-foreground">
            Data per {new Date(verdict.as_of).toLocaleString("id-ID")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
