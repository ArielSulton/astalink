"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Building2, Plus } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { useWorkspace } from "@/components/workspace-context";
import { api, type Business } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

export default function BusinessListPage() {
  const { workspaceId } = useWorkspace();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(false);

  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!workspaceId) return;
    let stale = false;
    const timer = window.setTimeout(() => {
      setLoading(true);
      (async () => {
        try {
          const sb = createClient();
          const { data: { session } } = await sb.auth.getSession();
          if (!session || stale) return;
          const result = await api.listBusinesses(
            workspaceId,
            session.access_token,
          );
          if (!stale) setBusinesses(result);
        } catch {
          if (!stale) toast.error("Gagal memuat daftar bisnis.");
        } finally {
          if (!stale) setLoading(false);
        }
      })();
    }, 0);
    return () => {
      stale = true;
      window.clearTimeout(timer);
    };
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
    <div className="mx-auto min-h-screen w-full max-w-4xl space-y-8 bg-background p-4 text-foreground sm:p-6 lg:p-8">
      <PageHeader eyebrow="Bisnis Saya" title="Daftar Bisnis" />

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
                  <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10px] font-medium text-muted-foreground">
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
        <div className="rounded-xl bg-card p-6 space-y-4 ring-1 ring-foreground/10">
          <div>
            <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">Nama Bisnis</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="cth. Toko Maju Jaya"
              className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
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
            className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground transition-all duration-200 hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground disabled:shadow-none"
          >
            <Plus className="h-4 w-4" />
            {creating ? "Menambahkan…" : "Tambah Bisnis"}
          </button>
        </div>
      </section>
    </div>
  );
}
