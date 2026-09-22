import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { DEFAULT_SORT } from "@/lib/transactions/sort";
import type { TransactionItem } from "@/lib/transactions/types";

import { TransactionView } from "./transaction-view";

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

function renderView(items: TransactionItem[], onSort = vi.fn()) {
  render(<TransactionView items={items} sort={DEFAULT_SORT} onSortChange={onSort} />);
  return onSort;
}

test("renders transaction semantics in table and card views", () => {
  renderView([tx({ id: "t1", ticker: "BBCA" })]);

  expect(screen.getAllByText("BBCA")).toHaveLength(2);
  expect(screen.getAllByText(/Rp 900.000/)).toHaveLength(2);
});

test("shows realized profit and loss with its sign", () => {
  renderView([tx({ id: "t1", side: "sell", realized_pnl: -125_000 })]);

  expect(screen.getAllByText(/-Rp 125.000/)).toHaveLength(2);
});

test("shows the broker reference when the order carries one", () => {
  renderView([tx({ id: "t1", broker_ref: "ORD-4471" })]);

  expect(screen.getAllByText("ORD-4471")).toHaveLength(2);
});

test("reports an order that has not been executed yet", () => {
  renderView([tx({ id: "t1", status: "pending", executed_at: null })]);

  expect(screen.getByText("Belum dieksekusi")).toBeInTheDocument();
});

test("asks the parent to re-sort when a column header is clicked", () => {
  const onSort = renderView([tx({ id: "t1" })]);

  fireEvent.click(screen.getByRole("button", { name: /Saham/ }));

  expect(onSort).toHaveBeenCalledWith("ticker");
});

test("marks the active sort column for assistive tech", () => {
  render(
    <TransactionView
      items={[tx({ id: "t1" })]}
      sort={{ key: "quantity", direction: "asc" }}
      onSortChange={vi.fn()}
    />,
  );

  expect(screen.getByRole("columnheader", { name: /Jumlah/ })).toHaveAttribute(
    "aria-sort",
    "ascending",
  );
});
