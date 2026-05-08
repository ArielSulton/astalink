"use client";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";

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
    <main className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold">Transactions</h1>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>
      {!workspaceId && <p className="text-muted-foreground">Pilih workspace untuk melihat transaksi.</p>}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th className="py-2">Date</th>
            <th>Ticker</th>
            <th>Side</th>
            <th>Qty</th>
            <th>Status</th>
            <th>Broker Ref</th>
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr key={t.id} className="border-b">
              <td className="py-2">{new Date(t.created_at).toLocaleString()}</td>
              <td>{t.ticker}</td>
              <td>{t.side}</td>
              <td>{t.quantity.toFixed(2)}</td>
              <td>{t.status}</td>
              <td className="font-mono text-xs">{t.broker_ref ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
