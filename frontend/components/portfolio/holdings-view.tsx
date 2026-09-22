import { ArrowDownRight, ArrowUpRight } from "lucide-react";

import type { HoldingView } from "@/lib/api-client";

type HoldingsViewProps = {
  holdings: HoldingView[];
  totalEquity: number | null;
  onBuy: (ticker: string) => void;
  onSell: (ticker: string) => void;
};

function idr(value: number | null | undefined): string {
  if (value == null) return "—";
  return `Rp ${value.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;
}

function signed(value: number | null | undefined): string {
  if (value == null) return "—";
  const formatted = value.toLocaleString("id-ID", { maximumFractionDigits: 0 });
  return `${value >= 0 ? "+Rp " : "-Rp "}${formatted.replace("-", "")}`;
}

function pnlClass(value: number | null | undefined): string {
  if (value == null) return "text-muted-foreground";
  return value >= 0 ? "text-chart-2" : "text-destructive";
}

function percentage(value: number | null): string {
  if (value == null) return "—";
  const percent = value * 100;
  return `${percent >= 0 ? "+" : ""}${percent.toFixed(2)}%`;
}

function portfolioShare(
  marketValue: number | null,
  totalEquity: number | null,
): string {
  if (marketValue == null || totalEquity == null || totalEquity === 0) return "—";
  return `${((marketValue / totalEquity) * 100).toFixed(1)}%`;
}

function HoldingActions({
  ticker,
  onBuy,
  onSell,
}: {
  ticker: string;
  onBuy: (ticker: string) => void;
  onSell: (ticker: string) => void;
}) {
  return (
    <div className="flex items-center justify-end gap-2">
      <button
        type="button"
        onClick={() => onBuy(ticker)}
        className="min-h-11 rounded-lg border border-chart-2/30 px-3 text-xs font-semibold text-chart-2 transition-all hover:bg-chart-2/10 lg:min-h-0 lg:px-2.5 lg:py-1.5"
      >
        Tambah
      </button>
      <button
        type="button"
        onClick={() => onSell(ticker)}
        className="min-h-11 rounded-lg border border-destructive/30 px-3 text-xs font-semibold text-destructive transition-all hover:bg-destructive/10 lg:min-h-0 lg:px-2.5 lg:py-1.5"
      >
        Jual
      </button>
    </div>
  );
}

export function HoldingsView({
  holdings,
  totalEquity,
  onBuy,
  onSell,
}: HoldingsViewProps) {
  return (
    <>
      <div className="space-y-3 p-3 lg:hidden">
        {holdings.map((holding) => (
          <article
            key={holding.ticker}
            className="rounded-xl border border-border bg-card p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-mono text-base font-bold text-foreground">
                  {holding.ticker}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {holding.quantity.toLocaleString("id-ID", {
                    maximumFractionDigits: 2,
                  })}{" "}
                  lembar · rata-rata {idr(holding.avg_cost)}
                </p>
              </div>
              <span className="rounded bg-secondary px-2 py-1 font-mono text-xs font-bold text-foreground">
                {portfolioShare(holding.market_value, totalEquity)}
              </span>
            </div>

            <dl className="mt-4 grid grid-cols-2 gap-3">
              <div>
                <dt className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Nilai pasar
                </dt>
                <dd className="mt-1 font-mono text-sm font-bold tabular-nums text-foreground">
                  {idr(holding.market_value)}
                </dd>
              </div>
              <div>
                <dt className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Untung / rugi
                </dt>
                <dd
                  className={`mt-1 font-mono text-sm font-bold tabular-nums ${pnlClass(
                    holding.unrealized_pnl,
                  )}`}
                >
                  {signed(holding.unrealized_pnl)} ·{" "}
                  {percentage(holding.unrealized_pnl_pct)}
                </dd>
              </div>
            </dl>

            <div className="mt-4 border-t border-border pt-3">
              <HoldingActions
                ticker={holding.ticker}
                onBuy={onBuy}
                onSell={onSell}
              />
            </div>
          </article>
        ))}
      </div>

      <div className="hidden overflow-x-auto lg:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/40 text-left font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              <th className="px-5 py-3">Saham</th>
              <th className="px-4 py-3 text-right">Modal Awal Invest</th>
              <th className="px-4 py-3 text-right">Harga Awal</th>
              <th className="px-4 py-3 text-right">Harga Sekarang</th>
              <th className="px-4 py-3 text-right">Nilai Pasar</th>
              <th className="px-4 py-3 text-right">Porsi Portofolio</th>
              <th className="px-4 py-3 text-right">
                Persentase Kenaikan / Retur
              </th>
              <th className="px-4 py-3 text-right">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((holding) => {
              const percent = holding.unrealized_pnl_pct;
              return (
                <tr
                  key={holding.ticker}
                  className="border-b border-border/60 transition-colors last:border-0 hover:bg-secondary/20"
                >
                  <td className="px-5 py-4">
                    <span className="block font-mono text-base font-bold">
                      {holding.ticker}
                    </span>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {holding.quantity.toLocaleString("id-ID", {
                        maximumFractionDigits: 2,
                      })}{" "}
                      lembar
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right font-mono font-semibold tabular-nums">
                    {idr(holding.cost_basis)}
                  </td>
                  <td className="px-4 py-4 text-right font-mono tabular-nums text-muted-foreground">
                    {idr(holding.avg_cost)}
                  </td>
                  <td className="px-4 py-4 text-right font-mono font-semibold tabular-nums">
                    {idr(holding.last_price)}
                  </td>
                  <td className="px-4 py-4 text-right font-mono font-bold tabular-nums">
                    {idr(holding.market_value)}
                  </td>
                  <td className="px-4 py-4 text-right font-mono text-xs font-medium tabular-nums">
                    <span className="rounded border border-border bg-secondary px-2 py-1 font-bold text-foreground">
                      {portfolioShare(holding.market_value, totalEquity)}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right">
                    <div
                      className={`inline-flex flex-col items-end ${pnlClass(
                        holding.unrealized_pnl,
                      )}`}
                    >
                      <span className="flex items-center gap-1 font-mono text-sm font-bold tabular-nums">
                        {percent != null &&
                          (percent >= 0 ? (
                            <ArrowUpRight className="size-4 shrink-0 text-chart-2" />
                          ) : (
                            <ArrowDownRight className="size-4 shrink-0 text-destructive" />
                          ))}
                        {percentage(percent)}
                      </span>
                      <span className="font-mono text-xs font-medium opacity-80">
                        {signed(holding.unrealized_pnl)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-right">
                    <HoldingActions
                      ticker={holding.ticker}
                      onBuy={onBuy}
                      onSell={onSell}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
