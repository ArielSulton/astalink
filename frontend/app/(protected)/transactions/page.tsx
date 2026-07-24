"use client";
import { useEffect, useState } from "react";
import { Receipt } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { useWorkspace } from "@/components/workspace-context";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";

interface Tx {
  id: string;
  audit_id?: string | null;
  workspace_id?: string | null;
  ticker: string;
  side: string;
  quantity: number;
  price?: number | null;
  status: string;
  broker_ref: string | null;
  created_at: string;
}

function idr(n: number | null | undefined): string {
  if (n == null) return "—";
  return "Rp " + n.toLocaleString("id-ID", { maximumFractionDigits: 0 });
}

export default function TransactionsPage() {
  const { workspaceId } = useWorkspace();
  const [items, setItems] = useState<Tx[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!workspaceId) {
      setItems([]);
      return;
    }
    setLoading(true);
    const sb = createClient();
    sb.from("transactions")
      .select("*")
      .eq("workspace_id", workspaceId)
      .order("created_at", { ascending: false })
      .then(({ data, error }) => {
        if (error) {
          console.error("Failed to load transactions:", error);
        }
        setItems((data as Tx[] | null) || []);
        setLoading(false);
      });
  }, [workspaceId]);

  return (
    <main className="p-8 max-w-5xl mx-auto bg-background min-h-screen text-foreground">
      <PageHeader eyebrow="Execution & Allocation Ledger" title="Riwayat Transaksi" className="mb-8" />

      {!workspaceId && (
        <EmptyState icon={Receipt} title="Pilih Workspace">
          Pilih workspace di kanan atas untuk melihat riwayat transaksi alokasi dana.
        </EmptyState>
      )}

      {workspaceId && loading && items.length === 0 && (
        <div className="p-8 text-center text-xs font-mono text-muted-foreground">
          Memuat riwayat transaksi…
        </div>
      )}

      {workspaceId && !loading && items.length === 0 && (
        <EmptyState icon={Receipt} title="Belum Ada Transaksi">
          Belum ada transaksi alokasi saham. Setiap kali Anda mengalokasikan dana ke saham (via Asisten AI atau Portofolio), riwayat transaksi akan muncul di sini.
        </EmptyState>
      )}

      {workspaceId && items.length > 0 && (
        <div className="rounded-2xl border border-border bg-card overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-secondary/40 text-left text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
                  <th className="px-5 py-3">Tanggal & Waktu</th>
                  <th className="px-4 py-3">Saham</th>
                  <th className="px-4 py-3">Jenis (Side)</th>
                  <th className="px-4 py-3 text-right">Jumlah (Qty)</th>
                  <th className="px-4 py-3 text-right">Harga / Lembar</th>
                  <th className="px-4 py-3 text-right">Total Nominal</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {items.map((t) => {
                  const isBuy = t.side.toLowerCase() === "buy";
                  const totalNominal = t.price != null ? t.quantity * t.price : null;
                  return (
                    <tr
                      key={t.id}
                      className="border-b border-border last:border-b-0 hover:bg-secondary/30 transition-colors duration-150"
                    >
                      <td className="px-5 py-3.5 font-mono text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(t.created_at).toLocaleDateString("id-ID", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                      <td className="px-4 py-3.5 font-mono font-bold text-foreground">
                        {t.ticker.replace(".JK", "")}
                      </td>
                      <td className="px-4 py-3.5">
                        <span
                          className={`inline-flex px-2.5 py-0.5 rounded-md text-[10px] font-bold font-mono uppercase tracking-wider border ${
                            isBuy
                              ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                              : "text-rose-400 bg-rose-500/10 border-rose-500/20"
                          }`}
                        >
                          {isBuy ? "BELI / ALOKASI" : "JUAL"}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right font-mono text-foreground tabular-nums">
                        {t.quantity.toLocaleString("id-ID", { maximumFractionDigits: 2 })} lembar
                      </td>
                      <td className="px-4 py-3.5 text-right font-mono text-muted-foreground tabular-nums">
                        {idr(t.price)}
                      </td>
                      <td className="px-4 py-3.5 text-right font-mono font-bold text-foreground tabular-nums">
                        {idr(totalNominal)}
                      </td>
                      <td className="px-4 py-3.5">
                        <StatusBadge status={t.status} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  );
}
