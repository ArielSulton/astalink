import { expect, test } from "vitest";

import { summarize } from "./summary";
import type { TransactionItem } from "./types";

function tx(overrides: Partial<TransactionItem> & { id: string }): TransactionItem {
  return {
    ticker: "BBCA.JK",
    side: "buy",
    quantity: 100,
    price: 9000,
    status: "filled",
    broker_ref: null,
    realized_pnl: null,
    executed_at: null,
    created_at: "2026-09-20T03:30:00Z",
    ...overrides,
  };
}

test("counts every row it is given", () => {
  expect(summarize([tx({ id: "a" }), tx({ id: "b" })]).count).toBe(2);
});

test("splits nominal value into buy and sell totals", () => {
  const items = [
    tx({ id: "a", side: "buy", quantity: 100, price: 9_000 }),
    tx({ id: "b", side: "sell", quantity: 50, price: 4_000 }),
  ];

  const result = summarize(items);

  expect(result.totalBuy).toBe(900_000);
  expect(result.totalSell).toBe(200_000);
});

test("ignores failed orders, which moved no money", () => {
  const items = [
    tx({ id: "ok", side: "buy", quantity: 100, price: 9_000 }),
    tx({ id: "dead", side: "buy", quantity: 100, price: 9_000, status: "failed" }),
  ];

  expect(summarize(items).totalBuy).toBe(900_000);
});

test("adds up realized profit and loss across sells", () => {
  const items = [
    tx({ id: "win", side: "sell", realized_pnl: 250_000 }),
    tx({ id: "loss", side: "sell", realized_pnl: -100_000 }),
    tx({ id: "open", side: "buy", realized_pnl: null }),
  ];

  expect(summarize(items).netPnl).toBe(150_000);
});

test("reports an empty ledger as zeroes", () => {
  expect(summarize([])).toEqual({ count: 0, totalBuy: 0, totalSell: 0, netPnl: 0 });
});
