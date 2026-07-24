"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Save } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspace } from "@/components/workspace-context";
import { api, type InvestorProfile } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

const EMPTY: InvestorProfile = {
  monthly_expenses: null,
  emergency_fund: null,
  capital_is_borrowed: null,
  horizon_months: null,
  net_worth: null,
  consumer_debt_interest_pct: null,
  available_hours_per_week: null,
  knows_sector: null,
};

const NUMBER_FIELDS: { key: keyof InvestorProfile; label: string; hint?: string }[] = [
  { key: "monthly_expenses", label: "Pengeluaran bulanan (Rp)" },
  { key: "emergency_fund", label: "Dana darurat saat ini (Rp)", hint: "< 6 bulan pengeluaran → semua alokasi dipaksa ke kas" },
  { key: "horizon_months", label: "Dana dibutuhkan dalam (bulan)", hint: "< 24 bulan → bisnis diveto (ilikuid)" },
  { key: "net_worth", label: "Kekayaan bersih (Rp)", hint: "Bisnis > 50% kekayaan bersih → diveto" },
  { key: "consumer_debt_interest_pct", label: "Bunga utang konsumtif tertinggi (0-1)", hint: "> 12% → lunasi dulu (imbal hasil bebas risiko)" },
  { key: "available_hours_per_week", label: "Jam tersedia per minggu" },
];

const BOOL_FIELDS: { key: keyof InvestorProfile; label: string; hint?: string }[] = [
  { key: "capital_is_borrowed", label: "Modal investasi dari pinjaman?", hint: "Ya → bisnis diveto sepenuhnya" },
  { key: "knows_sector", label: "Anda paham sektor bisnisnya?", hint: "Keunggulan informasi memengaruhi premium skor bisnis" },
];

export default function InvestorProfilePage() {
  const { workspaceId } = useWorkspace();
  const [profile, setProfile] = useState<InvestorProfile | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!workspaceId) return;
    (async () => {
      const { data: { session } } = await createClient().auth.getSession();
      if (!session) return;
      try {
        setProfile({ ...EMPTY, ...(await api.getInvestorProfile(workspaceId, session.access_token)) });
      } catch {
        toast.error("Gagal memuat profil investor.");
        setProfile(EMPTY);
      }
    })();
  }, [workspaceId]);

  async function save() {
    if (!profile || !workspaceId) return;
    const { data: { session } } = await createClient().auth.getSession();
    if (!session) { toast.error("Sesi berakhir, silakan login ulang."); return; }
    setSaving(true);
    try {
      await api.putInvestorProfile(workspaceId, profile, session.access_token);
      toast.success("Profil investor tersimpan.");
    } catch {
      toast.error("Gagal menyimpan profil investor.");
    } finally {
      setSaving(false);
    }
  }

  if (!profile) return <div className="p-6"><Skeleton className="h-64 w-full" /></div>;

  return (
    <div className="space-y-6 p-6">
      <PageHeader eyebrow="L0-2 — Personal Constraints" title="Profil Investor">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" render={<Link href="/allocation" />}>
            <ArrowLeft className="h-4 w-4 mr-1" />Kembali
          </Button>
          <Button onClick={save} disabled={saving} size="sm">
            <Save className="h-4 w-4 mr-1" />{saving ? "Menyimpan..." : "Simpan"}
          </Button>
        </div>
      </PageHeader>

      <p className="text-xs text-muted-foreground">
        Jawaban di sini punya otoritas <b>veto keras</b> — tidak ada skor bisnis atau saham
        yang bisa menimpanya. Kosong berarti pemeriksaan terkait tidak bisa dijalankan
        (dan itu ditampilkan, bukan disembunyikan).
      </p>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Kondisi keuangan pribadi</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          {NUMBER_FIELDS.map(({ key, label, hint }) => (
            <div key={key} className="space-y-1">
              <label className="text-[11px] font-medium">{label}</label>
              <input
                type="number"
                step="any"
                defaultValue={profile[key] === null ? "" : String(profile[key])}
                onBlur={(e) => {
                  const n = e.target.value.trim() === "" ? null : Number(e.target.value);
                  setProfile((p) => p && { ...p, [key]: n !== null && Number.isFinite(n) ? n : null });
                }}
                className="h-8 w-full rounded border border-border bg-background px-2 text-xs"
              />
              {hint && <p className="text-[10px] text-muted-foreground">{hint}</p>}
            </div>
          ))}
          {BOOL_FIELDS.map(({ key, label, hint }) => (
            <div key={key} className="space-y-1">
              <label className="text-[11px] font-medium">{label}</label>
              <select
                value={profile[key] === null ? "" : String(profile[key])}
                onChange={(e) => {
                  const v = e.target.value === "" ? null : e.target.value === "true";
                  setProfile((p) => p && { ...p, [key]: v });
                }}
                className="h-8 w-full rounded border border-border bg-background px-2 text-xs"
              >
                <option value="">— Belum dijawab —</option>
                <option value="true">Ya</option>
                <option value="false">Tidak</option>
              </select>
              {hint && <p className="text-[10px] text-muted-foreground">{hint}</p>}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
