"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft, Save, Building2, Activity, TrendingUp, Calculator, Wallet,
  Target, Handshake, User, Shield, DoorOpen, Users, Cloud, CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { IntakeField, type FieldKind } from "@/components/allocation/intake-field";
import { IntakeSectionHeader } from "@/components/allocation/intake-section-header";
import { IntakeProgressSidebar, type SectionStatus } from "@/components/allocation/intake-progress-sidebar";
import { api, type EvidenceTag, type IntakeProfile, type TaggedField } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

interface FieldDef {
  key: string;
  label: string;
  kind: FieldKind;
  options?: string[];
  hint?: string;
  prefix?: string;
  suffix?: string;
}

interface BlockDef {
  key: string;
  label: string;
  icon: LucideIcon;
  fields: FieldDef[];
}

const BLOCKS: BlockDef[] = [
  { key: "identity", label: "Identitas", icon: Building2, fields: [
    { key: "sector", label: "Sektor", kind: "text" },
    { key: "business_model", label: "Model bisnis", kind: "text" },
    { key: "b2b_or_b2c", label: "B2B / B2C", kind: "select", options: ["b2b", "b2c", "campuran"] },
    { key: "location", label: "Lokasi", kind: "text" },
  ]},
  { key: "current_state", label: "Kondisi saat ini", icon: Activity, fields: [
    { key: "stage", label: "Tahap", kind: "select", options: ["idea", "pre_revenue", "early_revenue", "profitable", "scaling"] },
    { key: "age_months", label: "Umur", kind: "number", suffix: "bulan" },
    { key: "headcount", label: "Jumlah karyawan", kind: "number" },
  ]},
  { key: "traction", label: "Traksi", icon: TrendingUp, fields: [
    { key: "monthly_revenue", label: "Omzet bulanan 12 bln", kind: "number_list", hint: "Contoh: 50jt, 60jt, 80jt (terlama → terbaru)" },
    { key: "growth_rate", label: "Pertumbuhan", kind: "number", suffix: "% / bln" },
    { key: "gross_margin", label: "Gross margin", kind: "number", suffix: "%" },
    { key: "customer_count", label: "Jumlah pelanggan", kind: "number" },
    { key: "retention_rate", label: "Retensi", kind: "number", suffix: "%" },
  ]},
  { key: "unit_economics", label: "Unit economics", icon: Calculator, fields: [
    { key: "price", label: "Harga jual/unit", kind: "number", prefix: "Rp" },
    { key: "cogs_per_unit", label: "HPP/unit", kind: "number", prefix: "Rp" },
    { key: "cac", label: "CAC", kind: "number", prefix: "Rp" },
    { key: "ltv", label: "LTV", kind: "number", prefix: "Rp" },
    { key: "contribution_margin", label: "Margin kontribusi/unit", kind: "number", prefix: "Rp" },
    { key: "payback_months", label: "Payback", kind: "number", suffix: "bulan" },
  ]},
  { key: "cash", label: "Kas", icon: Wallet, fields: [
    { key: "cash_on_hand", label: "Kas di tangan", kind: "number", prefix: "Rp" },
    { key: "monthly_burn", label: "Burn bulanan", kind: "number", prefix: "Rp" },
    { key: "runway_months", label: "Runway", kind: "number", suffix: "bulan" },
    { key: "is_profitable", label: "Sudah profit?", kind: "bool" },
  ]},
  { key: "capital_need", label: "Kebutuhan modal", icon: Target, fields: [
    { key: "amount", label: "Total kebutuhan", kind: "number", prefix: "Rp" },
    { key: "breakdown", label: "Rincian penggunaan", kind: "breakdown", hint: "Satu baris per pos: tujuan: jumlah — mis. marketing: 50000000" },
    { key: "consequence_if_unfunded", label: "Konsekuensi jika tidak didanai", kind: "text" },
  ]},
  { key: "deal_structure", label: "Struktur deal", icon: Handshake, fields: [
    { key: "instrument", label: "Instrumen", kind: "select", options: ["equity", "loan", "convertible", "profit_share"] },
    { key: "ownership_pct", label: "Kepemilikan yang didapat", kind: "number", suffix: "%" },
    { key: "interest_rate", label: "Bunga (jika pinjaman)", kind: "number", suffix: "%" },
  ]},
  { key: "user_role", label: "Peran Anda", icon: User, fields: [
    { key: "operator_or_passive", label: "Operator / pasif", kind: "select", options: ["operator", "passive"] },
    { key: "hours_per_week", label: "Jam per minggu", kind: "number" },
  ]},
  { key: "control", label: "Kontrol", icon: Shield, fields: [
    { key: "ownership_pct", label: "Kepemilikan setelah masuk", kind: "number", suffix: "%" },
    { key: "veto_rights", label: "Punya hak veto?", kind: "bool" },
    { key: "shareholder_agreement_exists", label: "Ada shareholder agreement?", kind: "bool" },
  ]},
  { key: "exit", label: "Exit", icon: DoorOpen, fields: [
    { key: "mechanism", label: "Mekanisme exit", kind: "text" },
    { key: "expected_timeline_months", label: "Perkiraan waktu exit", kind: "number", suffix: "bulan" },
  ]},
  { key: "team", label: "Tim", icon: Users, fields: [
    { key: "operator_identity", label: "Siapa operatornya", kind: "text" },
    { key: "track_record", label: "Rekam jejak", kind: "text" },
    { key: "founder_capital_contributed", label: "Modal disetor pendiri", kind: "number", prefix: "Rp" },
  ]},
];

function emptyProfile(): IntakeProfile {
  const p: IntakeProfile = {};
  for (const block of BLOCKS) {
    p[block.key] = {};
    for (const f of block.fields) p[block.key][f.key] = { value: null, evidence: "unknown" };
  }
  return p;
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

function blockCompleted(p: IntakeProfile, block: BlockDef): number {
  let count = 0;
  for (const f of block.fields) {
    const field = p[block.key]?.[f.key];
    if (field && field.value !== null && field.evidence !== "unknown") count += 1;
  }
  return count;
}

export default function IntakePage({ params }: { params: Promise<{ businessId: string }> }) {
  const { businessId } = use(params);
  const [profile, setProfile] = useState<IntakeProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "dirty" | "saving" | "saved">("idle");
  const [openBlocks, setOpenBlocks] = useState<Record<string, boolean>>({ identity: true });
  const [activeSection, setActiveSection] = useState<string>("identity");
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const profileRef = useRef<IntakeProfile | null>(null);

  useEffect(() => {
    (async () => {
      const { data: { session } } = await createClient().auth.getSession();
      if (!session) return;
      try {
        const fetched = await api.getIntakeProfile(businessId, session.access_token);
        const base = emptyProfile();
        for (const bk of Object.keys(fetched ?? {})) {
          for (const fk of Object.keys(fetched[bk] ?? {})) {
            if (base[bk]?.[fk] !== undefined) base[bk][fk] = fetched[bk][fk];
          }
        }
        setProfile(base);
        profileRef.current = base;
      } catch {
        toast.error("Gagal memuat profil intake.");
        const empty = emptyProfile();
        setProfile(empty);
        profileRef.current = empty;
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
    return total > 0 ? known / total : 0;
  }, [profile]);

  const sections: SectionStatus[] = useMemo(() => {
    if (!profile) return [];
    return BLOCKS.map((block) => ({
      key: block.key,
      label: block.label,
      icon: block.icon,
      completed: blockCompleted(profile, block),
      total: block.fields.length,
    }));
  }, [profile]);

  const setSectionRef = useCallback((key: string) => (el: HTMLElement | null) => {
    sectionRefs.current[key] = el;
  }, []);

  function update(blockKey: string, fieldKey: string, patch: Partial<TaggedField>) {
    let next: IntakeProfile | null = null;
    setProfile((p) => {
      if (!p) return p;
      const field = { ...p[blockKey][fieldKey], ...patch };
      if (patch.value !== undefined && patch.value !== null && field.evidence === "unknown") {
        field.evidence = "claimed";
      }
      if (patch.value === null) field.evidence = "unknown";
      next = { ...p, [blockKey]: { ...p[blockKey], [fieldKey]: field } };
      return next;
    });
    setSaveState("dirty");
    // Debounced auto-save — always snapshots the freshest profile via the ref
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      profileRef.current = next ?? profileRef.current;
      if (profileRef.current) saveProfile(profileRef.current);
    }, 2000);
  }

  async function saveProfile(p: IntakeProfile, manual = false) {
    const { data: { session } } = await createClient().auth.getSession();
    if (!session) { toast.error("Sesi berakhir, silakan login ulang."); setSaveState("idle"); return; }
    try {
      await api.putIntakeProfile(businessId, p, session.access_token);
      setSaveState("saved");
      if (manual) toast.success("Profil intake tersimpan.");
      setTimeout(() => setSaveState("idle"), 2000);
    } catch {
      setSaveState("idle");
      if (manual) toast.error("Gagal menyimpan profil intake.");
    }
  }

  async function manualSave() {
    if (!profile) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setSaving(true);
    await saveProfile(profile, true);
    setSaving(false);
  }

  // Scroll spy — track which section is in view
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const key = entry.target.getAttribute("data-block");
            if (key) setActiveSection(key);
          }
        }
      },
      { rootMargin: "-20% 0px -70% 0px", threshold: 0 }
    );
    Object.values(sectionRefs.current).forEach((el) => el && observer.observe(el));
    return () => observer.disconnect();
  }, [sections.length > 0]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!profile) return;
    Object.values(sectionRefs.current).forEach((el) => el && el.removeAttribute("data-observe"));
  }, [profile]);

  function scrollToSection(key: string) {
    const el = sectionRefs.current[key];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      // Section may be collapsed — expand it then scroll
      setOpenBlocks((b) => ({ ...b, [key]: true }));
      requestAnimationFrame(() => {
        setTimeout(() => sectionRefs.current[key]?.scrollIntoView({ behavior: "smooth", block: "start" }), 250);
      });
    }
  }

  useEffect(() => () => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
  }, []);

  if (!profile) return <div className="p-6"><Skeleton className="h-64 w-full" /></div>;

  return (
    <div className="space-y-6 p-6">
      <PageHeader eyebrow="B0 — Pendataan Bisnis" title="Profil Intake Bisnis">
        <div className="flex items-center gap-3 flex-wrap">
          {/* Auto-save status */}
          <span className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground">
            {saveState === "saving" ? (
              <Cloud className="h-3.5 w-3.5 animate-pulse" /> 
            ) : saveState === "saved" ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-chart-2" />
            ) : (
              <Cloud className="h-3.5 w-3.5" />
            )}
            {saveState === "saved" ? "Tersimpan" : saveState === "saving" ? "Menyimpan..." : saveState === "dirty" ? "Belum tersimpan" : "Auto-save aktif"}
          </span>
          <span className="text-xs font-mono text-muted-foreground">
            Kelengkapan: <b className="text-foreground">{(completeness * 100).toFixed(0)}%</b>
            {completeness < 0.4 && <span className="text-destructive"> (&lt;40% → INSUFFICIENT)</span>}
          </span>
          <Button variant="outline" size="sm" render={<Link href="/allocation" />}>
            <ArrowLeft className="h-4 w-4 mr-1" />Kembali
          </Button>
          <Button onClick={manualSave} disabled={saving || saveState === "saving"} size="sm">
            <Save className="h-4 w-4 mr-1" />{saving ? "Menyimpan..." : "Simpan"}
          </Button>
        </div>
      </PageHeader>

      <p className="text-xs text-muted-foreground">
        Setiap field membawa tag bukti. <b>VERIFIED</b> = didukung dokumen; <b>CLAIMED</b> = kata pemilik
        (bobot skoring jauh lebih rendah); <b>UNKNOWN</b> tidak pernah diisi default oleh sistem.
      </p>

      <div className="grid gap-6 lg:grid-cols-[220px_1fr] items-start">
        {/* Sidebar — sticky on desktop */}
        <aside className="hidden lg:block lg:sticky lg:top-6">
          <IntakeProgressSidebar
            sections={sections}
            activeSection={activeSection}
            onSectionClick={scrollToSection}
          />
        </aside>

        {/* Content */}
        <div className="min-w-0 space-y-4">
          {BLOCKS.map((block) => {
            const completed = blockCompleted(profile, block);
            const isOpen = !!openBlocks[block.key];
            const hasSection = completed > 0;
            return (
              <Card
                key={block.key}
                data-block={block.key}
                ref={setSectionRef(block.key)}
                className={hasSection ? "ring-chart-2/20" : undefined}
              >
                <Collapsible
                  open={isOpen}
                  onOpenChange={(o: boolean) => setOpenBlocks((b) => ({ ...b, [block.key]: o }))}
                >
                  <CollapsibleTrigger className="flex w-full items-center gap-2 px-(--card-spacing) pt-3 pb-2 text-left transition-colors hover:bg-secondary/40 rounded-t-xl">
                    <IntakeSectionHeader
                      label={block.label}
                      icon={block.icon}
                      completed={completed}
                      total={block.fields.length}
                      isOpen={isOpen}
                    />
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <CardContent className="grid gap-5 md:grid-cols-2 pt-2">
                      {block.fields.map((f) => {
                        const field = profile[block.key]?.[f.key];
                        const tag = (field?.evidence ?? "unknown") as EvidenceTag;
                        const fieldId = `${block.key}-${f.key}`;
                        return (
                          <IntakeField
                            key={f.key}
                            fieldId={fieldId}
                            label={f.label}
                            kind={f.kind}
                            value={displayValue(f.kind, field)}
                            evidenceTag={tag}
                            options={f.options}
                            hint={f.hint}
                            prefix={f.prefix}
                            suffix={f.suffix}
                            onValueChange={(v) => update(block.key, f.key, { value: v as never })}
                            onEvidenceChange={(t) => update(block.key, f.key, { evidence: t })}
                          />
                        );
                      })}
                    </CardContent>
                  </CollapsibleContent>
                </Collapsible>
              </Card>
            );
          })}

          <div className="flex justify-end">
            <Button onClick={manualSave} disabled={saving || saveState === "saving"}>
              <Save className="h-4 w-4 mr-1" />{saving ? "Menyimpan..." : "Simpan Profil"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
