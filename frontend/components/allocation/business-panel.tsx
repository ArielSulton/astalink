"use client";

import { AlertTriangle, ChevronDown, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { DevilsAdvocateFinding, Layer0Result, QualitySubScore, VetoFlag } from "@/lib/api-client";

const SEVERITY_STYLES: Record<DevilsAdvocateFinding["severity"], string> = {
  critical: "text-rose-400 bg-rose-500/10 border-rose-500/30",
  warning: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  info: "text-sky-400 bg-sky-500/10 border-sky-500/30",
};

/** L0-2 vetoes: prominent and non-dismissible. A veto is not advice. */
export function VetoPanel({ flags }: { flags: VetoFlag[] }) {
  if (flags.length === 0) return null;
  return (
    <div className="space-y-2">
      {flags.map((f, i) => (
        <div
          key={i}
          className={cn(
            "flex items-start gap-2 rounded-lg border px-3 py-2.5",
            f.hard
              ? "border-rose-500/50 bg-rose-500/10"
              : "border-amber-500/40 bg-amber-500/5",
          )}
        >
          <ShieldAlert className={cn("h-4 w-4 mt-0.5 shrink-0", f.hard ? "text-rose-400" : "text-amber-400")} />
          <div>
            <p className={cn("text-[10px] font-black font-mono uppercase tracking-wider", f.hard ? "text-rose-400" : "text-amber-400")}>
              {f.hard ? "VETO KERAS" : "PERINGATAN"} · {f.code}
            </p>
            <p className="text-xs text-foreground mt-0.5">{f.reason}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function QualityRow({ sub }: { sub: QualitySubScore }) {
  return (
    <Collapsible>
      <CollapsibleTrigger className="flex w-full items-center justify-between gap-2 rounded border border-border px-3 py-2 hover:bg-secondary/50">
        <span className="text-xs font-mono font-bold">{sub.code} · {sub.label}</span>
        <span className="flex items-center gap-2">
          <span className={cn("text-sm font-mono font-bold", sub.score === null && "text-rose-400")}>
            {sub.score === null ? "UNKNOWN" : `${sub.score.toFixed(0)}/100`}
          </span>
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        </span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <ul className="mt-1 mb-2 space-y-1 pl-3">
          {sub.checks.map((c, i) => (
            <li key={i} className="flex items-center gap-2 text-[11px]">
              <span
                className={cn(
                  "px-1.5 rounded font-mono font-bold text-[9px] border",
                  c.passed === true && "text-emerald-400 border-emerald-500/30",
                  c.passed === false && "text-rose-400 border-rose-500/30",
                  c.passed === null && "text-rose-400 border-rose-500/30 border-dashed",
                )}
              >
                {c.passed === true ? "PASS" : c.passed === false ? "FAIL" : "UNKNOWN"}
              </span>
              <span className="text-muted-foreground">{c.detail}</span>
            </li>
          ))}
        </ul>
      </CollapsibleContent>
    </Collapsible>
  );
}

export function BusinessPanel({ layer0 }: { layer0: Layer0Result }) {
  const quality = layer0.quality;
  return (
    <div className="space-y-4">
      <VetoPanel flags={layer0.veto_flags} />

      {layer0.rejected_reasons.length > 0 && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/5 px-3 py-2.5">
          <p className="text-[10px] font-black font-mono uppercase tracking-wider text-rose-400 mb-1">
            Hard reject (STEP 2)
          </p>
          <ul className="space-y-0.5 pl-4 list-disc text-xs text-foreground">
            {layer0.rejected_reasons.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      {quality && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Kualitas Bisnis (Q1–Q5)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {quality.subscores.map((s) => <QualityRow key={s.code} sub={s} />)}
            <p className="text-[10px] text-muted-foreground font-mono pt-1">
              Klasifikasi tujuan dana: <span className="font-bold text-foreground uppercase">{quality.q5_purpose}</span>
            </p>
          </CardContent>
        </Card>
      )}

      {layer0.devils_advocate.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Devil&apos;s Advocate (DB1–DB7)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {layer0.devils_advocate.map((f, i) => (
              <Collapsible key={i}>
                <CollapsibleTrigger className="flex w-full items-center justify-between gap-2 rounded border border-border px-3 py-2 hover:bg-secondary/50">
                  <span className="flex items-center gap-2 text-xs">
                    <span className={cn("px-1.5 py-0.5 rounded text-[9px] font-bold font-mono border", SEVERITY_STYLES[f.severity])}>
                      {f.severity.toUpperCase()}
                    </span>
                    <span className="font-mono font-bold">{f.code}</span>
                    <span className="text-muted-foreground">{f.title}</span>
                  </span>
                  <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <p className="px-3 py-2 text-[11px] text-muted-foreground flex gap-2">
                    <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                    {f.finding}
                  </p>
                </CollapsibleContent>
              </Collapsible>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
