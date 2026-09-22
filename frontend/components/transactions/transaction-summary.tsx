import { ArrowDownLeft, ArrowUpRight, Receipt, TrendingUp } from "lucide-react";

import { StatCard } from "@/components/ui/stat-card";
import { idr, signedIdr } from "@/lib/transactions/format";
import type { TransactionSummary } from "@/lib/transactions/summary";
import { cn } from "@/lib/utils";

interface TransactionSummaryCardsProps {
  summary: TransactionSummary;
  filtered: boolean;
}

export function TransactionSummaryCards({
  summary,
  filtered,
}: TransactionSummaryCardsProps) {
  const scope = filtered ? "Hasil filter saat ini" : "Seluruh riwayat";

  return (
    <div
      role="group"
      aria-label="Ringkasan transaksi"
      className="grid grid-cols-2 gap-3 lg:grid-cols-4"
    >
      <StatCard
        label="Transaksi"
        value={summary.count.toLocaleString("id-ID")}
        icon={Receipt}
        hint={scope}
      />
      <StatCard
        label="Total Beli"
        value={idr(summary.totalBuy)}
        icon={ArrowDownLeft}
        hint="Order gagal tidak dihitung"
      />
      <StatCard
        label="Total Jual"
        value={idr(summary.totalSell)}
        icon={ArrowUpRight}
        hint="Order gagal tidak dihitung"
      />
      <StatCard
        label="Net Realized P&L"
        value={signedIdr(summary.netPnl)}
        icon={TrendingUp}
        hint="Dari posisi yang sudah ditutup"
        valueClassName={cn(
          summary.netPnl < 0 && "text-destructive",
          summary.netPnl > 0 && "text-chart-2",
        )}
      />
    </div>
  );
}
