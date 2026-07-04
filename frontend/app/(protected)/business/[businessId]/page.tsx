"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Building2, Coins, TrendingUp } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/page-header";
import { StatCard } from "@/components/ui/stat-card";
import { api, LAST_BUSINESS_KEY, type BusinessDetail } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

export default function BusinessDetailPage() {
  const { businessId } = useParams<{ businessId: string }>();

  const [business, setBusiness] = useState<BusinessDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const [periodYear, setPeriodYear] = useState(String(new Date().getFullYear()));
  const [aset, setAset] = useState("");
  const [omset, setOmset] = useState("");
  const [profit, setProfit] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      setBusiness(await api.getBusiness(businessId, session.access_token));
      localStorage.setItem(LAST_BUSINESS_KEY, businessId);
    } catch {
      setNotFound(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [businessId]);

  async function handleAddRecord() {
    const year = parseInt(periodYear, 10);
    const asetNum = parseFloat(aset);
    const omsetNum = parseFloat(omset);
    const profitNum = parseFloat(profit);
    if (!year || Number.isNaN(asetNum) || Number.isNaN(omsetNum) || Number.isNaN(profitNum)) {
      toast.error("Isi semua kolom dengan angka yang valid.");
      return;
    }

    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) { toast.error("Sesi berakhir, silakan login ulang."); return; }

    setSaving(true);
    try {
      await api.addFinancialRecord(
        businessId,
        { period_year: year, aset: asetNum, omset: omsetNum, profit: profitNum },
        session.access_token,
      );
      toast.success(`Data tahun ${year} tersimpan.`);
      setAset(""); setOmset(""); setProfit("");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal menyimpan data.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="p-8 text-muted-foreground text-sm">Memuat…</div>;
  }

  if (notFound || !business) {
    return (
      <div className="p-8 max-w-4xl w-full mx-auto">
        <p className="text-sm text-muted-foreground">Bisnis tidak ditemukan.</p>
      </div>
    );
  }

  const latest = business.financial_records[0]; // backend orders period_year desc

  return (
    <div className="p-8 space-y-8 max-w-4xl w-full mx-auto bg-background min-h-screen text-foreground">
      <PageHeader eyebrow={business.industry || "Bisnis"} title={business.name} />
      {business.description && (
        <p className="text-sm text-muted-foreground -mt-6">{business.description}</p>
      )}

      <section className="grid grid-cols-3 gap-4">
        <StatCard
          label="Aset Terkini"
          value={latest ? `Rp ${latest.aset.toLocaleString("id-ID")}` : "—"}
          icon={Building2}
          hint={latest ? `Tahun ${latest.period_year}` : "Belum ada data"}
        />
        <StatCard
          label="Omset Terkini"
          value={latest ? `Rp ${latest.omset.toLocaleString("id-ID")}` : "—"}
          icon={Coins}
          hint={latest ? `Tahun ${latest.period_year}` : "Belum ada data"}
        />
        <StatCard
          label="Profit Terkini"
          value={latest ? `Rp ${latest.profit.toLocaleString("id-ID")}` : "—"}
          icon={TrendingUp}
          hint={latest ? `Tahun ${latest.period_year}` : "Belum ada data"}
        />
      </section>

      <section className="space-y-3">
        <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
          Riwayat Keuangan
        </h2>
        {business.financial_records.length === 0 ? (
          <p className="text-sm text-muted-foreground p-4 rounded-xl border border-border bg-card">
            Belum ada data keuangan. Tambahkan lewat form di bawah.
          </p>
        ) : (
          <div className="rounded-xl border border-border bg-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground text-xs uppercase tracking-wider font-mono">
                  <th className="text-left p-3">Tahun</th>
                  <th className="text-right p-3">Aset</th>
                  <th className="text-right p-3">Omset</th>
                  <th className="text-right p-3">Profit</th>
                </tr>
              </thead>
              <tbody>
                {business.financial_records.map((r) => (
                  <tr key={r.id} className="border-b border-border last:border-0">
                    <td className="p-3 font-mono">{r.period_year}</td>
                    <td className="p-3 text-right font-mono">Rp {r.aset.toLocaleString("id-ID")}</td>
                    <td className="p-3 text-right font-mono">Rp {r.omset.toLocaleString("id-ID")}</td>
                    <td className="p-3 text-right font-mono">Rp {r.profit.toLocaleString("id-ID")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
          Tambah / Perbarui Data Tahunan
        </h2>
        <div className="rounded-2xl border border-border bg-card p-6 space-y-4 shadow-xl">
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">Tahun</label>
              <input
                type="number"
                value={periodYear}
                onChange={(e) => setPeriodYear(e.target.value)}
                className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">Aset (Rp)</label>
              <input
                type="number"
                value={aset}
                onChange={(e) => setAset(e.target.value)}
                placeholder="0"
                className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">Omset (Rp)</label>
              <input
                type="number"
                value={omset}
                onChange={(e) => setOmset(e.target.value)}
                placeholder="0"
                className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">Profit (Rp)</label>
              <input
                type="number"
                value={profit}
                onChange={(e) => setProfit(e.target.value)}
                placeholder="0"
                className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200"
              />
            </div>
          </div>
          <button
            onClick={handleAddRecord}
            disabled={saving}
            className="w-full py-3 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed disabled:shadow-none transition-all duration-200"
          >
            {saving ? "Menyimpan…" : "Simpan Data Tahunan"}
          </button>
        </div>
      </section>
    </div>
  );
}
