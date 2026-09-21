import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";

import { StatusBadge } from "@/components/ui/status-badge";
import { bareTicker } from "@/lib/transactions/filter";
import { formatDateTime, idr, shares, signedIdr } from "@/lib/transactions/format";
import { nominal, type SortKey, type TransactionSort } from "@/lib/transactions/sort";
import type { TransactionItem } from "@/lib/transactions/types";
import { cn } from "@/lib/utils";

interface TransactionViewProps {
  items: TransactionItem[];
  sort: TransactionSort;
  onSortChange: (key: SortKey) => void;
}

function SideBadge({ side }: { side: string }) {
  const isBuy = side.toLowerCase() === "buy";
  return (
    <span
      className={`inline-flex rounded-md border px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider ${
        isBuy
          ? "border-chart-2/20 bg-chart-2/10 text-chart-2"
          : "border-destructive/20 bg-destructive/10 text-destructive"
      }`}
    >
      {isBuy ? "BELI / ALOKASI" : "JUAL"}
    </span>
  );
}

function PnlText({ value, className }: { value: number | null | undefined; className?: string }) {
  if (value == null) {
    return <span className={cn("text-muted-foreground", className)}>—</span>;
  }
  return (
    <span className={cn(value < 0 ? "text-destructive" : "text-chart-2", className)}>
      {signedIdr(value)}
    </span>
  );
}

const SORT_ICONS = { asc: ArrowUp, desc: ArrowDown };

function SortableHeader({
  label,
  sortKey,
  sort,
  onSortChange,
  align = "left",
}: {
  label: string;
  sortKey: SortKey;
  sort: TransactionSort;
  onSortChange: (key: SortKey) => void;
  align?: "left" | "right";
}) {
  const active = sort.key === sortKey;
  const Icon = active ? SORT_ICONS[sort.direction] : ChevronsUpDown;

  return (
    <th
      scope="col"
      aria-sort={
        active ? (sort.direction === "asc" ? "ascending" : "descending") : "none"
      }
      className={cn("px-4 py-3", align === "right" && "text-right")}
    >
      <button
        type="button"
        onClick={() => onSortChange(sortKey)}
        className={cn(
          "inline-flex items-center gap-1.5 transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
          align === "right" && "flex-row-reverse",
          active && "text-foreground",
        )}
      >
        {label}
        <Icon className={cn("size-3", active ? "opacity-100" : "opacity-40")} aria-hidden />
      </button>
    </th>
  );
}

export function TransactionView({ items, sort, onSortChange }: TransactionViewProps) {
  return (
    <>
      <div className="space-y-3 lg:hidden">
        {items.map((item) => {
          const total = nominal(item);
          const isBuy = item.side.toLowerCase() === "buy";
          return (
            <article
              key={item.id}
              className="rounded-xl border border-border bg-card p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-mono text-base font-bold text-foreground">
                    {bareTicker(item.ticker)}
                  </h2>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {shares(item.quantity)} · {idr(item.price)} / lembar
                  </p>
                </div>
                <p className="shrink-0 font-mono text-sm font-bold tabular-nums text-foreground">
                  {total == null ? "—" : `${isBuy ? "-" : "+"}${idr(total)}`}
                </p>
              </div>

              {item.realized_pnl != null && (
                <div className="mt-3 flex items-center justify-between gap-3 border-t border-border pt-3">
                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    Realized P&amp;L
                  </span>
                  <PnlText
                    value={item.realized_pnl}
                    className="font-mono text-sm font-bold tabular-nums"
                  />
                </div>
              )}

              <div className="mt-4 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <SideBadge side={item.side} />
                  <StatusBadge status={item.status} />
                </div>
                <time className="text-right font-mono text-[11px] text-muted-foreground">
                  {formatDateTime(item.created_at)}
                </time>
              </div>

              {item.broker_ref && (
                <p className="mt-3 font-mono text-[10px] text-muted-foreground/70">
                  Ref broker: <span className="text-muted-foreground">{item.broker_ref}</span>
                </p>
              )}
            </article>
          );
        })}
      </div>

      <div className="hidden overflow-x-auto lg:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/40 text-left font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              <SortableHeader
                label="Tanggal Dibuat"
                sortKey="created_at"
                sort={sort}
                onSortChange={onSortChange}
              />
              <th scope="col" className="px-4 py-3">
                Eksekusi
              </th>
              <SortableHeader
                label="Saham"
                sortKey="ticker"
                sort={sort}
                onSortChange={onSortChange}
              />
              <th scope="col" className="px-4 py-3">
                Jenis (Side)
              </th>
              <SortableHeader
                label="Jumlah (Qty)"
                sortKey="quantity"
                sort={sort}
                onSortChange={onSortChange}
                align="right"
              />
              <SortableHeader
                label="Harga / Lembar"
                sortKey="price"
                sort={sort}
                onSortChange={onSortChange}
                align="right"
              />
              <SortableHeader
                label="Total Nominal"
                sortKey="nominal"
                sort={sort}
                onSortChange={onSortChange}
                align="right"
              />
              <SortableHeader
                label="Realized P&L"
                sortKey="realized_pnl"
                sort={sort}
                onSortChange={onSortChange}
                align="right"
              />
              <th scope="col" className="px-4 py-3">
                Status
              </th>
              <th scope="col" className="px-4 py-3">
                Ref Broker
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                className="border-b border-border transition-colors duration-150 last:border-b-0 hover:bg-secondary/30"
              >
                <td className="whitespace-nowrap px-4 py-3.5 font-mono text-xs text-muted-foreground">
                  {formatDateTime(item.created_at)}
                </td>
                <td className="whitespace-nowrap px-4 py-3.5 font-mono text-xs text-muted-foreground">
                  {item.executed_at ? (
                    formatDateTime(item.executed_at)
                  ) : (
                    <span className="text-muted-foreground/60">Belum dieksekusi</span>
                  )}
                </td>
                <td className="px-4 py-3.5 font-mono font-bold text-foreground">
                  {bareTicker(item.ticker)}
                </td>
                <td className="px-4 py-3.5">
                  <SideBadge side={item.side} />
                </td>
                <td className="whitespace-nowrap px-4 py-3.5 text-right font-mono tabular-nums text-foreground">
                  {shares(item.quantity)}
                </td>
                <td className="px-4 py-3.5 text-right font-mono tabular-nums text-muted-foreground">
                  {idr(item.price)}
                </td>
                <td className="px-4 py-3.5 text-right font-mono font-bold tabular-nums text-foreground">
                  {idr(nominal(item))}
                </td>
                <td className="px-4 py-3.5 text-right font-mono font-bold tabular-nums">
                  <PnlText value={item.realized_pnl} />
                </td>
                <td className="px-4 py-3.5">
                  <StatusBadge status={item.status} />
                </td>
                <td className="px-4 py-3.5 font-mono text-xs text-muted-foreground">
                  {item.broker_ref ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
