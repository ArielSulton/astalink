"use client";

import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { EvidenceBadge } from "@/components/allocation/evidence-badge";
import type { EvidenceTag } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export type FieldKind = "number" | "text" | "bool" | "select" | "number_list" | "breakdown";

const EVIDENCE_OPTIONS: EvidenceTag[] = ["verified", "claimed", "estimated", "unknown"];

interface IntakeFieldProps {
  fieldId: string;
  label: string;
  kind: FieldKind;
  value: string;
  evidenceTag: EvidenceTag;
  options?: string[];
  hint?: string;
  prefix?: string;
  suffix?: string;
  onValueChange: (value: unknown) => void;
  onEvidenceChange: (tag: EvidenceTag) => void;
}

function EvidenceSelector({ tag, onChange }: { tag: EvidenceTag; onChange: (t: EvidenceTag) => void }) {
  return (
    <div className="flex items-center gap-1.5">
      <EvidenceBadge tag={tag} className="scale-90 origin-right" />
      <select
        value={tag}
        onChange={(e) => onChange(e.target.value as EvidenceTag)}
        className="h-6 rounded border border-border bg-background px-1 text-[10px] text-muted-foreground cursor-pointer"
        aria-label="Tag bukti"
      >
        {EVIDENCE_OPTIONS.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </div>
  );
}

function FieldInput({ fieldId, kind, value, options, hint, onValueChange }: {
  fieldId: string;
  kind: FieldKind;
  value: string;
  options?: string[];
  hint?: string;
  onValueChange: (v: unknown) => void;
}) {
  switch (kind) {
    case "bool": {
      const checked = value === "true";
      return (
        <div className="flex items-center gap-2.5 h-8">
          <Switch
            checked={checked}
            onCheckedChange={(c: boolean) => onValueChange(c ? "true" : "false")}
            size="sm"
          />
          <span className="text-xs text-muted-foreground font-medium">
            {checked ? "Ya" : "Tidak"}
          </span>
        </div>
      );
    }

    case "select":
      return (
        <select
          id={fieldId}
          value={value}
          onChange={(e) => onValueChange(e.target.value || null)}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <option value="">— Belum dijawab —</option>
          {(options ?? []).map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      );

    case "breakdown":
      return (
        <>
          <textarea
            id={fieldId}
            defaultValue={value}
            onBlur={(e) => onValueChange(e.target.value)}
            placeholder={hint}
            rows={3}
            className="w-full rounded-lg border border-input bg-transparent px-2.5 py-1.5 text-sm font-mono outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 resize-none"
          />
          {hint && <p className="text-[10px] text-muted-foreground/70 mt-0.5">{hint}</p>}
        </>
      );

    case "number_list":
      return (
        <>
          <Input
            id={fieldId}
            defaultValue={value}
            onBlur={(e) => {
              const raw = e.target.value.trim();
              if (!raw) { onValueChange(null); return; }
              const nums = raw.split(",").map((s) => Number(s.trim())).filter((n) => Number.isFinite(n));
              onValueChange(nums.length ? nums : null);
            }}
            placeholder="50000000, 60000000, 80000000"
            className="h-8 text-sm font-mono"
          />
          <p className="text-[10px] text-muted-foreground/70 mt-0.5">Pisahkan dengan koma, terlama ke terbaru</p>
        </>
      );

    default:
      return (
        <Input
          id={fieldId}
          defaultValue={value}
          onBlur={(e) => {
            const raw = e.target.value.trim();
            if (!raw) { onValueChange(null); return; }
            if (kind === "number") {
              const n = Number(raw);
              onValueChange(Number.isFinite(n) ? n : null);
            } else {
              onValueChange(raw);
            }
          }}
          placeholder={kind === "number" ? "0" : ""}
          type={kind === "number" ? "text" : "text"}
          inputMode={kind === "number" ? "decimal" : "text"}
          className="h-8 text-sm font-mono"
        />
      );
  }
}

export function IntakeField({
  fieldId,
  label,
  kind,
  value,
  evidenceTag,
  options,
  hint,
  prefix,
  suffix,
  onValueChange,
  onEvidenceChange,
}: IntakeFieldProps) {
  const hasValue = value !== "" && value !== null && value !== undefined;

  return (
    <div className="space-y-1.5">
      {/* Label + Evidence row */}
      <div className="flex items-center justify-between gap-2">
        <label htmlFor={fieldId} className="text-[11px] font-medium text-foreground">
          {label}
        </label>
        <EvidenceSelector tag={evidenceTag} onChange={onEvidenceChange} />
      </div>

      {/* Input with optional prefix/suffix */}
      <div className={cn("flex items-center gap-2", (prefix || suffix) && "gap-1.5")}>
        {prefix && (
          <span className="text-[10px] text-muted-foreground font-mono shrink-0 tabular-nums">{prefix}</span>
        )}
        <div className="flex-1 min-w-0">
          <FieldInput
            fieldId={fieldId}
            kind={kind}
            value={value}
            options={options}
            hint={hint}
            onValueChange={onValueChange}
          />
        </div>
        {suffix && (
          <span className="text-[10px] text-muted-foreground font-mono shrink-0">{suffix}</span>
        )}
      </div>

      {/* Auto-evidence warning */}
      {hasValue && evidenceTag === "unknown" && (
        <p className="text-[10px] text-amber-400 font-medium">Pilih tag bukti</p>
      )}
    </div>
  );
}
