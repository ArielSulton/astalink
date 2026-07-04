"use client";
import { useEffect, useState } from "react";
import { Receipt } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";

interface Tx {
  id: string;
  audit_id: string;
  ticker: string;
  side: string;
  quantity: number;
  status: string;
  broker_ref: string | null;
  created_at: string;
}

export default function TransactionsPage() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [items, setItems] = useState<Tx[]>([]);

  useEffect(() => {
    if (!workspaceId) return;
    const sb = createClient();
    // RLS-scoped: only transactions belonging to audits in the user's workspaces.
    sb.from("transactions")
      .select("*, audit_log!inner(workspace_id)")
      .eq("audit_log.workspace_id", workspaceId)
      .order("created_at", { ascending: false })
      .then(({ data }) => setItems((data as Tx[] | null) || []));
  }, [workspaceId]);

  return (
    <main className="p-8 max-w-4xl mx-auto bg-background min-h-screen text-foreground">
      <PageHeader eyebrow="Execution Ledger" title="Transactions" className="mb-8">
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </PageHeader>

      {!workspaceId && (
        <EmptyState icon={Receipt} title="Pilih Workspace">
          Pilih workspace di kanan atas untuk melihat riwayat transaksi tereksekusi.
        </EmptyState>
      )}

      {workspaceId && items.length === 0 && (
        <EmptyState icon={Receipt} title="Belum Ada Transaksi">
          Transaksi akan muncul di sini setelah alokasi yang Anda setujui dieksekusi.
        </EmptyState>
      )}

      {workspaceId && items.length > 0 && (
        <div className="rounded-2xl border border-border bg-card overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-secondary/40 text-left text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
                  <th className="px-5 py-3">Tanggal</th>
                  <th className="px-4 py-3">Ticker</th>
                  <th className="px-4 py-3">Side</th>
                  <th className="px-4 py-3 text-right">Qty</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-5 py-3">Broker Ref</th>
                </tr>
              </thead>
              <tbody>
                {items.map((t) => {
                  const isBuy = t.side.toLowerCase() === "buy";
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
                          className={`inline-flex px-2 py-0.5 rounded-md text-[10px] font-bold font-mono uppercase tracking-wider border ${
                            isBuy
                              ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                              : "text-rose-400 bg-rose-500/10 border-rose-500/20"
                          }`}
                        >
                          {t.side}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right font-mono text-foreground tabular-nums">
                        {t.quantity.toFixed(2)}
                      </td>
                      <td className="px-4 py-3.5">
                        <StatusBadge status={t.status} />
                      </td>
                      <td className="px-5 py-3.5 font-mono text-xs text-muted-foreground">
                        {t.broker_ref ?? "—"}
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
