"use client";

import { use, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Save } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { EvidenceBadge } from "@/components/allocation/evidence-badge";
import { api, type EvidenceTag, type IntakeProfile, type TaggedField } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

type FieldKind = "number" | "text" | "bool" | "select" | "number_list" | "breakdown";

interface FieldDef {
  key: string;
  label: string;
  kind: FieldKind;
  options?: string[];
  hint?: string;
}

// Mirrors backend BusinessProfile block-by-block. Every field carries an
// evidence tag; UNKNOWN is the default, never silently coerced.
const BLOCKS: { key: string; label: string; fields: FieldDef[] }[] = [
  { key: "identity", label: "Identitas", fields: [
    { key: "sector", label: "Sektor", kind: "text" },
    { key: "business_model", label: "Model bisnis", kind: "text" },
    { key: "b2b_or_b2c", label: "B2B / B2C", kind: "select", options: ["b2b", "b2c", "campuran"] },
    { key: "location", label: "Lokasi", kind: "text" },
  ]},
  { key: "current_state", label: "Kondisi saat ini", fields: [
    { key: "stage", label: "Tahap", kind: "select", options: ["idea", "pre_revenue", "early_revenue", "profitable", "scaling"] },
    { key: "age_months", label: "Umur (bulan)", kind: "number" },
    { key: "headcount", label: "Jumlah karyawan", kind: "number" },
  ]},
  { key: "traction", label: "Traksi", fields: [
    { key: "monthly_revenue", label: "Omzet bulanan 12 bln", kind: "number_list", hint: "Pisahkan dengan koma, terlama → terbaru" },
    { key: "growth_rate", label: "Pertumbuhan/bln (0.05 = 5%)", kind: "number" },
    { key: "gross_margin", label: "Gross margin (0-1)", kind: "number" },
    { key: "customer_count", label: "Jumlah pelanggan", kind: "number" },
    { key: "retention_rate", label: "Retensi (0-1)", kind: "number" },
  ]},
  { key: "unit_economics", label: "Unit economics", fields: [
    { key: "price", label: "Harga jual/unit (Rp)", kind: "number" },
    { key: "cogs_per_unit", label: "HPP/unit (Rp)", kind: "number" },
    { key: "cac", label: "CAC (Rp)", kind: "number" },
    { key: "ltv", label: "LTV (Rp)", kind: "number" },
    { key: "contribution_margin", label: "Margin kontribusi/unit (Rp)", kind: "number" },
    { key: "payback_months", label: "Payback (bulan)", kind: "number" },
  ]},
  { key: "cash", label: "Kas", fields: [
    { key: "cash_on_hand", label: "Kas di tangan (Rp)", kind: "number" },
    { key: "monthly_burn", label: "Burn bulanan (Rp)", kind: "number" },
    { key: "runway_months", label: "Runway (bulan)", kind: "number" },
    { key: "is_profitable", label: "Sudah profit?", kind: "bool" },
  ]},
  { key: "capital_need", label: "Kebutuhan modal", fields: [
    { key: "amount", label: "Total kebutuhan (Rp)", kind: "number" },
    { key: "breakdown", label: "Rincian penggunaan", kind: "breakdown", hint: "Satu baris per pos: tujuan: jumlah — mis. marketing: 50000000" },
    { key: "consequence_if_unfunded", label: "Konsekuensi jika tidak didanai", kind: "text" },
  ]},
  { key: "deal_structure", label: "Struktur deal", fields: [
    { key: "instrument", label: "Instrumen", kind: "select", options: ["equity", "loan", "convertible", "profit_share"] },
    { key: "ownership_pct", label: "% kepemilikan yang didapat (0-1)", kind: "number" },
    { key: "interest_rate", label: "Bunga (jika pinjaman, 0-1)", kind: "number" },
  ]},
  { key: "user_role", label: "Peran Anda", fields: [
    { key: "operator_or_passive", label: "Operator / pasif", kind: "select", options: ["operator", "passive"] },
    { key: "hours_per_week", label: "Jam per minggu", kind: "number" },
  ]},
  { key: "control", label: "Kontrol", fields: [
    { key: "ownership_pct", label: "% kepemilikan setelah masuk (0-1)", kind: "number" },
    { key: "veto_rights", label: "Punya hak veto?", kind: "bool" },
    { key: "shareholder_agreement_exists", label: "Ada shareholder agreement?", kind: "bool" },
  ]},
  { key: "exit", label: "Exit", fields: [
    { key: "mechanism", label: "Mekanisme exit", kind: "text" },
    { key: "expected_timeline_months", label: "Perkiraan waktu exit (bulan)", kind: "number" },
  ]},
  { key: "team", label: "Tim", fields: [
    { key: "operator_identity", label: "Siapa operatornya", kind: "text" },
    { key: "track_record", label: "Rekam jejak", kind: "text" },
    { key: "founder_capital_contributed", label: "Modal disetor pendiri (Rp)", kind: "number" },
  ]},
];

const EVIDENCE_OPTIONS: EvidenceTag[] = ["verified", "claimed", "estimated", "unknown"];

function emptyProfile(): IntakeProfile {
  const p: IntakeProfile = {};
  for (const block of BLOCKS) {
    p[block.key] = {};
    for (const f of block.fields) p[block.key][f.key] = { value: null, evidence: "unknown" };
  }
  return p;
}

function serializeValue(kind: FieldKind, raw: string): unknown {
  const t = raw.trim();
  if (!t) return null;
  if (kind === "number") { const n = Number(t); return Number.isFinite(n) ? n : null; }
  if (kind === "number_list") {
    const nums = t.split(",").map((s) => Number(s.trim())).filter((n) => Number.isFinite(n));
    return nums.length ? nums : null;
  }
  if (kind === "breakdown") {
    const items = t.split("\n").map((line) => {
      const idx = line.lastIndexOf(":");
      if (idx < 0) return null;
      const amount = Number(line.slice(idx + 1).trim());
      const purpose = line.slice(0, idx).trim();
      return purpose && Number.isFinite(amount) ? { purpose, amount } : null;
    }).filter(Boolean);
    return items.length ? items : null;
  }
  if (kind === "bool") return t === "true" ? true : t === "false" ? false : null;
  return t;
}

function displayValue(kind: FieldKind, field: TaggedField | undefined): string {
  const v = field?.value;
  if (v === null || v === undefined) return "";
  if (kind === "number_list" && Array.isArray(v)) return v.join(", ");
  if (kind === "breakdown" && Array.isArray(v)) {
    return (v as { purpose: string; amount: number }[])
      .map((i) => `${i.purpose}: ${i.amount}`).join("\n");
  }
  return String(v);
}

export default function IntakePage({ params }: { params: Promise<{ businessId: string }> }) {
  const { businessId } = use(params);
  const [profile, setProfile] = useState<IntakeProfile | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      const { data: { session } } = await createClient().auth.getSession();
      if (!session) return;
      try {
        const fetched = await api.getIntakeProfile(businessId, session.access_token);
        // merge over an empty skeleton so new fields always render
        const base = emptyProfile();
        for (const bk of Object.keys(fetched ?? {})) {
          for (const fk of Object.keys(fetched[bk] ?? {})) {
            if (base[bk]?.[fk] !== undefined) base[bk][fk] = fetched[bk][fk];
          }
        }
        setProfile(base);
      } catch {
        toast.error("Gagal memuat profil intake.");
        setProfile(emptyProfile());
      }
    })();
  }, [businessId]);

  const completeness = useMemo(() => {
    if (!profile) return 0;
    let known = 0, total = 0;
    for (const block of BLOCKS) for (const f of block.fields) {
      total += 1;
      const field = profile[block.key]?.[f.key];
      if (field && field.evidence !== "unknown" && field.value !== null) known += 1;
    }
    return known / total;
  }, [profile]);

  function update(blockKey: string, fieldKey: string, patch: Partial<TaggedField>) {
    setProfile((p) => {
      if (!p) return p;
      const field = { ...p[blockKey][fieldKey], ...patch };
      // value present but tag left UNKNOWN → the honest default is CLAIMED
      if (patch.value !== undefined && patch.value !== null && field.evidence === "unknown") {
        field.evidence = "claimed";
      }
      if (patch.value === null) field.evidence = "unknown";
      return { ...p, [blockKey]: { ...p[blockKey], [fieldKey]: field } };
    });
  }

  async function save() {
    if (!profile) return;
    const { data: { session } } = await createClient().auth.getSession();
    if (!session) { toast.error("Sesi berakhir, silakan login ulang."); return; }
    setSaving(true);
    try {
      await api.putIntakeProfile(businessId, profile, session.access_token);
      toast.success("Profil intake tersimpan.");
    } catch {
      toast.error("Gagal menyimpan profil intake.");
    } finally {
      setSaving(false);
    }
  }

  if (!profile) return <div className="p-6"><Skeleton className="h-64 w-full" /></div>;

  return (
    <div className="space-y-6 p-6">
      <PageHeader eyebrow="B0 — Business Intake" title="Profil Intake Bisnis">
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-muted-foreground">
            Kelengkapan: <b className="text-foreground">{(completeness * 100).toFixed(0)}%</b>
            {completeness < 0.4 && <span className="text-rose-400"> (&lt;40% → INSUFFICIENT)</span>}
          </span>
          <Button variant="outline" size="sm" render={<Link href="/allocation" />}>
            <ArrowLeft className="h-4 w-4 mr-1" />Kembali
          </Button>
          <Button onClick={save} disabled={saving} size="sm">
            <Save className="h-4 w-4 mr-1" />{saving ? "Menyimpan..." : "Simpan"}
          </Button>
        </div>
      </PageHeader>

      <p className="text-xs text-muted-foreground">
        Setiap field membawa tag bukti. <b>VERIFIED</b> = didukung dokumen; <b>CLAIMED</b> = kata pemilik
        (bobot skoring jauh lebih rendah); <b>UNKNOWN</b> tidak pernah diisi default oleh sistem.
      </p>

      {BLOCKS.map((block) => (
        <Card key={block.key}>
          <CardHeader className="pb-2"><CardTitle className="text-sm">{block.label}</CardTitle></CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            {block.fields.map((f) => {
              const field = profile[block.key]?.[f.key];
              const tag = (field?.evidence ?? "unknown") as EvidenceTag;
              return (
                <div key={f.key} className="space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <label className="text-[11px] font-medium">{f.label}</label>
                    <div className="flex items-center gap-1.5">
                      <EvidenceBadge tag={tag} />
                      <select
                        value={tag}
                        onChange={(e) => update(block.key, f.key, { evidence: e.target.value as EvidenceTag })}
                        className="h-6 rounded border border-border bg-background px-1 text-[10px]"
                        aria-label={`Bukti untuk ${f.label}`}
                      >
                        {EVIDENCE_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                      </select>
                    </div>
                  </div>
                  {f.kind === "bool" || f.kind === "select" ? (
                    <select
                      value={displayValue(f.kind, field)}
                      onChange={(e) => update(block.key, f.key, { value: serializeValue(f.kind, e.target.value) })}
                      className="h-8 w-full rounded border border-border bg-background px-2 text-xs"
                    >
                      <option value="">— UNKNOWN —</option>
                      {(f.kind === "bool" ? ["true", "false"] : f.options ?? []).map((o) => (
                        <option key={o} value={o}>{f.kind === "bool" ? (o === "true" ? "Ya" : "Tidak") : o}</option>
                      ))}
                    </select>
                  ) : f.kind === "breakdown" ? (
                    <textarea
                      defaultValue={displayValue(f.kind, field)}
                      onBlur={(e) => update(block.key, f.key, { value: serializeValue(f.kind, e.target.value) })}
                      placeholder={f.hint}
                      rows={3}
                      className="w-full rounded border border-border bg-background px-2 py-1 text-xs font-mono"
                    />
                  ) : (
                    <input
                      defaultValue={displayValue(f.kind, field)}
                      onBlur={(e) => update(block.key, f.key, { value: serializeValue(f.kind, e.target.value) })}
                      placeholder={f.hint ?? (f.kind === "number" ? "0" : "")}
                      className="h-8 w-full rounded border border-border bg-background px-2 text-xs"
                    />
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      ))}

      <div className="flex justify-end">
        <Button onClick={save} disabled={saving}>
          <Save className="h-4 w-4 mr-1" />{saving ? "Menyimpan..." : "Simpan Profil"}
        </Button>
      </div>
    </div>
  );
}
