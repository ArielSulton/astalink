"use client";

import { Receipt } from "lucide-react";
import { useEffect, useState } from "react";

import { TransactionExplorer } from "@/components/transactions/transaction-explorer";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { useWorkspace } from "@/components/workspace-context";
import { createClient } from "@/lib/supabase/client";
import type { TransactionItem } from "@/lib/transactions/types";

export default function TransactionsPage() {
  const { workspaceId } = useWorkspace();
  const [items, setItems] = useState<TransactionItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let stale = false;
    const timer = window.setTimeout(() => {
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
          if (stale) return;
          if (error) {
            console.error("Failed to load transactions:", error);
          }
          setItems((data as TransactionItem[] | null) || []);
          setLoading(false);
        });
    }, 0);
    return () => {
      stale = true;
      window.clearTimeout(timer);
    };
  }, [workspaceId]);

  return (
    <main className="mx-auto min-h-screen max-w-7xl bg-background p-4 text-foreground sm:p-6 lg:p-8">
      <PageHeader
        eyebrow="Eksekusi & Alokasi"
        title="Riwayat Transaksi"
        className="mb-8"
      />

      {!workspaceId && (
        <EmptyState icon={Receipt} title="Pilih Workspace">
          Pilih workspace di bagian atas untuk melihat riwayat transaksi
          alokasi dana.
        </EmptyState>
      )}

      {workspaceId && loading && items.length === 0 && (
        <div className="p-8 text-center font-mono text-xs text-muted-foreground">
          Memuat riwayat transaksi…
        </div>
      )}

      {workspaceId && !loading && items.length === 0 && (
        <EmptyState icon={Receipt} title="Belum Ada Transaksi">
          Belum ada transaksi alokasi saham. Setiap kali Anda mengalokasikan
          dana ke saham, riwayat transaksi akan muncul di sini.
        </EmptyState>
      )}

      {workspaceId && items.length > 0 && <TransactionExplorer items={items} />}
    </main>
  );
}
