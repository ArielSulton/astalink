import { nominal } from "./sort";
import type { TransactionItem } from "./types";

export interface TransactionSummary {
  count: number;
  totalBuy: number;
  totalSell: number;
  netPnl: number;
}

export function summarize(items: TransactionItem[]): TransactionSummary {
  let totalBuy = 0;
  let totalSell = 0;
  let netPnl = 0;

  for (const item of items) {
    netPnl += item.realized_pnl ?? 0;

    // A failed order never reached the market, so it moved no rupiah.
    if (item.status.toLowerCase() === "failed") continue;

    const value = nominal(item) ?? 0;
    if (item.side.toLowerCase() === "sell") totalSell += value;
    else totalBuy += value;
  }

  return { count: items.length, totalBuy, totalSell, netPnl };
}
