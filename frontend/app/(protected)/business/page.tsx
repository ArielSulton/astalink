"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Building2, Plus } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { api, type Business } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

export default function BusinessListPage() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(false);

  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!workspaceId) return;
    setLoading(true);
    (async () => {
      try {
        const sb = createClient();
        const { data: { session } } = await sb.auth.getSession();
        if (!session) return;
        setBusinesses(await api.listBusinesses(workspaceId, session.access_token));
      } catch {
        toast.error("Gagal memuat daftar bisnis.");
      } finally {
        setLoading(false);
      }
    })();
  }, [workspaceId]);

  async function handleCreate() {
    if (!workspaceId) { toast.error("Pilih workspace terlebih dahulu."); return; }
    if (!name.trim()) { toast.error("Nama bisnis wajib diisi."); return; }

    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) { toast.error("Sesi berakhir, silakan login ulang."); return; }

    setCreating(true);
    try {
      const business = await api.createBusiness(
        {
          name: name.trim(),
          workspace_id: workspaceId,
          industry: industry.trim() || undefined,
          description: description.trim() || undefined,
        },
        session.access_token,
      );
      setBusinesses((prev) => [business, ...prev]);
      setName(""); setIndustry(""); setDescription("");
      toast.success(`Bisnis "${business.name}" ditambahkan.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal menambahkan bisnis.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="p-8 space-y-8 max-w-4xl w-full mx-auto bg-background min-h-screen text-foreground">
      <PageHeader eyebrow="Bisnis Saya" title="List Bisnis">
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </PageHeader>

      <section className="space-y-3">
        <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
          Daftar Bisnis
        </h2>

        {loading && (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="h-16 rounded-xl bg-card animate-pulse border border-border" />
            ))}
          </div>
        )}

        {!loading && !workspaceId && (
          <EmptyState icon={Building2} title="Pilih workspace">
            Pilih workspace di atas untuk melihat daftar bisnis.
          </EmptyState>
        )}

        {!loading && workspaceId && businesses.length === 0 && (
          <EmptyState icon={Building2} title="Belum ada bisnis">
            Tambahkan bisnis pertama Anda lewat form di bawah.
          </EmptyState>
        )}

        {!loading && businesses.length > 0 && (
          <div className="space-y-2.5">
            {businesses.map((b) => (
              <Link
                key={b.id}
                href={`/business/${b.id}`}
                className="flex items-start gap-3.5 p-4 rounded-xl border border-border bg-card hover:border-border/60 hover:bg-secondary/30 transition-all duration-200"
              >
                <div className="w-8 h-8 rounded-lg bg-chart-2/10 flex items-center justify-center border border-chart-2/20 mt-0.5 shrink-0">
                  <Building2 className="h-4 w-4 text-chart-2" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground font-semibold truncate leading-tight">{b.name}</p>
                  <div className="flex items-center gap-2 mt-1.5 text-[10px] text-muted-foreground font-medium">
                    {b.industry && (
                      <span className="px-1.5 py-0.5 rounded bg-secondary border border-border font-mono text-[9px] font-bold uppercase tracking-wider text-foreground">
                        {b.industry}
                      </span>
                    )}
                    <span className="font-mono">
                      {new Date(b.created_at).toLocaleDateString("id-ID", {
                        day: "numeric", month: "short", year: "numeric",
                      })}
                    </span>
                  </div>
                  {b.description && (
                    <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">{b.description}</p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
          Tambah Bisnis Baru
        </h2>
        <div className="rounded-2xl border border-border bg-card p-6 space-y-4 shadow-xl">
          <div>
            <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">Nama Bisnis</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="cth. Toko Maju Jaya"
              className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">Industri (opsional)</label>
              <input
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="cth. Ritel, F&B"
                className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">Deskripsi (opsional)</label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Deskripsi singkat"
                className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200"
              />
            </div>
          </div>
          <button
            onClick={handleCreate}
            disabled={!name.trim() || creating}
            className="w-full py-3 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed disabled:shadow-none transition-all duration-200 flex items-center justify-center gap-2"
          >
            <Plus className="h-4 w-4" />
            {creating ? "Menambahkan…" : "Tambah Bisnis"}
          </button>
        </div>
      </section>
    </div>
  );
}
