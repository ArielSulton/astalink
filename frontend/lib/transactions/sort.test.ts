import { expect, test } from "vitest";

import { DEFAULT_SORT, nominal, sortTransactions, toggleSort } from "./sort";
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

test("defaults to the newest transaction first", () => {
  const items = [
    tx({ id: "old", created_at: "2026-09-01T00:00:00Z" }),
    tx({ id: "new", created_at: "2026-09-20T00:00:00Z" }),
  ];

  expect(sortTransactions(items, DEFAULT_SORT).map((i) => i.id)).toEqual(["new", "old"]);
});

test("sorts tickers alphabetically by their bare symbol", () => {
  const items = [tx({ id: "t", ticker: "TLKM.JK" }), tx({ id: "b", ticker: "BBCA.JK" })];

  const result = sortTransactions(items, { key: "ticker", direction: "asc" });

  expect(result.map((i) => i.id)).toEqual(["b", "t"]);
});

test("sorts by total nominal rather than unit price", () => {
  const items = [
    tx({ id: "small", quantity: 10, price: 10_000 }),
    tx({ id: "big", quantity: 500, price: 1_000 }),
  ];

  const result = sortTransactions(items, { key: "nominal", direction: "desc" });

  expect(result.map((i) => i.id)).toEqual(["big", "small"]);
});

test("pushes rows with no value to the bottom in either direction", () => {
  const items = [tx({ id: "blank", realized_pnl: null }), tx({ id: "value", realized_pnl: 5_000 })];

  const asc = sortTransactions(items, { key: "realized_pnl", direction: "asc" });
  const desc = sortTransactions(items, { key: "realized_pnl", direction: "desc" });

  expect(asc.map((i) => i.id)).toEqual(["value", "blank"]);
  expect(desc.map((i) => i.id)).toEqual(["value", "blank"]);
});

test("leaves the caller's array untouched", () => {
  const items = [
    tx({ id: "old", created_at: "2026-09-01T00:00:00Z" }),
    tx({ id: "new", created_at: "2026-09-20T00:00:00Z" }),
  ];

  sortTransactions(items, DEFAULT_SORT);

  expect(items.map((i) => i.id)).toEqual(["old", "new"]);
});

test("flips direction when the same column is toggled again", () => {
  expect(toggleSort({ key: "ticker", direction: "asc" }, "ticker")).toEqual({
    key: "ticker",
    direction: "desc",
  });
});

test("starts a newly picked column descending", () => {
  expect(toggleSort({ key: "ticker", direction: "asc" }, "quantity")).toEqual({
    key: "quantity",
    direction: "desc",
  });
});

test("reads nominal as quantity times price, or nothing without a price", () => {
  expect(nominal(tx({ id: "a", quantity: 100, price: 9_000 }))).toBe(900_000);
  expect(nominal(tx({ id: "b", price: null }))).toBeNull();
});
