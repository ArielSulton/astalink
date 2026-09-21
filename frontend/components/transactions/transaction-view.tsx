import { StatusBadge } from "@/components/ui/status-badge";

export interface TransactionItem {
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

function idr(value: number | null | undefined): string {
  if (value == null) return "—";
  return `Rp ${value.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function nominal(item: TransactionItem): number | null {
  return item.price != null ? item.quantity * item.price : null;
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

export function TransactionView({ items }: { items: TransactionItem[] }) {
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
                    {item.ticker.replace(".JK", "")}
                  </h2>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {item.quantity.toLocaleString("id-ID", {
                      maximumFractionDigits: 2,
                    })}{" "}
                    lembar · {idr(item.price)} / lembar
                  </p>
                </div>
                <p className="shrink-0 font-mono text-sm font-bold tabular-nums text-foreground">
                  {total == null ? "—" : `${isBuy ? "-" : "+"}${idr(total)}`}
                </p>
              </div>
              <div className="mt-4 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <SideBadge side={item.side} />
                  <StatusBadge status={item.status} />
                </div>
                <time className="text-right font-mono text-[11px] text-muted-foreground">
                  {formatDate(item.created_at)}
                </time>
              </div>
            </article>
          );
        })}
      </div>

      <div className="hidden overflow-x-auto lg:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/40 text-left font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
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
            {items.map((item) => (
              <tr
                key={item.id}
                className="border-b border-border transition-colors duration-150 last:border-b-0 hover:bg-secondary/30"
              >
                <td className="whitespace-nowrap px-5 py-3.5 font-mono text-xs text-muted-foreground">
                  {formatDate(item.created_at)}
                </td>
                <td className="px-4 py-3.5 font-mono font-bold text-foreground">
                  {item.ticker.replace(".JK", "")}
                </td>
                <td className="px-4 py-3.5">
                  <SideBadge side={item.side} />
                </td>
                <td className="px-4 py-3.5 text-right font-mono tabular-nums text-foreground">
                  {item.quantity.toLocaleString("id-ID", {
                    maximumFractionDigits: 2,
                  })}{" "}
                  lembar
                </td>
                <td className="px-4 py-3.5 text-right font-mono tabular-nums text-muted-foreground">
                  {idr(item.price)}
                </td>
                <td className="px-4 py-3.5 text-right font-mono font-bold tabular-nums text-foreground">
                  {idr(nominal(item))}
                </td>
                <td className="px-4 py-3.5">
                  <StatusBadge status={item.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
