import { expect, test } from "vitest";

import { DEFAULT_FILTERS, filterTransactions, hasActiveFilters } from "./filter";
import type { TransactionItem } from "./types";

const NOW = new Date("2026-09-21T00:00:00Z");

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

test("keeps every item when no filter is active", () => {
  const items = [tx({ id: "a" }), tx({ id: "b", side: "sell", status: "pending" })];

  expect(filterTransactions(items, DEFAULT_FILTERS, NOW)).toHaveLength(2);
});

test("matches the query against the ticker, ignoring case and the .JK suffix", () => {
  const items = [tx({ id: "a", ticker: "BBCA.JK" }), tx({ id: "b", ticker: "TLKM.JK" })];

  const result = filterTransactions(items, { ...DEFAULT_FILTERS, query: "bbca" }, NOW);

  expect(result.map((i) => i.id)).toEqual(["a"]);
});

test("matches the query against the broker ref", () => {
  const items = [tx({ id: "a", broker_ref: "ORD-991" }), tx({ id: "b", broker_ref: "ORD-002" })];

  const result = filterTransactions(items, { ...DEFAULT_FILTERS, query: "991" }, NOW);

  expect(result.map((i) => i.id)).toEqual(["a"]);
});

test("keeps only the requested side", () => {
  const items = [tx({ id: "a", side: "buy" }), tx({ id: "b", side: "sell" })];

  const result = filterTransactions(items, { ...DEFAULT_FILTERS, side: "sell" }, NOW);

  expect(result.map((i) => i.id)).toEqual(["b"]);
});

test("keeps only the requested status", () => {
  const items = [tx({ id: "a", status: "filled" }), tx({ id: "b", status: "failed" })];

  const result = filterTransactions(items, { ...DEFAULT_FILTERS, status: "failed" }, NOW);

  expect(result.map((i) => i.id)).toEqual(["b"]);
});

test("drops items created before the range window", () => {
  const items = [
    tx({ id: "recent", created_at: "2026-09-18T00:00:00Z" }),
    tx({ id: "old", created_at: "2026-08-01T00:00:00Z" }),
  ];

  const result = filterTransactions(items, { ...DEFAULT_FILTERS, range: "7d" }, NOW);

  expect(result.map((i) => i.id)).toEqual(["recent"]);
});

test("treats the default filter set as inactive", () => {
  expect(hasActiveFilters(DEFAULT_FILTERS)).toBe(false);
});

test("treats a whitespace-only query as inactive", () => {
  expect(hasActiveFilters({ ...DEFAULT_FILTERS, query: "   " })).toBe(false);
});

test("flags any filter that deviates from the default", () => {
  expect(hasActiveFilters({ ...DEFAULT_FILTERS, status: "failed" })).toBe(true);
  expect(hasActiveFilters({ ...DEFAULT_FILTERS, query: "bbca" })).toBe(true);
});
