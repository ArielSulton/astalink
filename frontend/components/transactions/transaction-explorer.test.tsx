import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";

import type { TransactionItem } from "@/lib/transactions/types";

import { TransactionExplorer } from "./transaction-explorer";

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

function many(count: number): TransactionItem[] {
  return Array.from({ length: count }, (_, i) =>
    tx({
      id: `t${i}`,
      ticker: `T${String(i).padStart(3, "0")}.JK`,
      created_at: new Date(Date.UTC(2026, 8, 20, 0, 0, i)).toISOString(),
    }),
  );
}

function bodyRows(): HTMLElement[] {
  const table = screen.getByRole("table");
  const [, ...rows] = within(table).getAllByRole("row");
  return rows;
}

test("narrows the table to rows matching the typed query", () => {
  render(
    <TransactionExplorer
      items={[tx({ id: "a", ticker: "BBCA.JK" }), tx({ id: "b", ticker: "TLKM.JK" })]}
    />,
  );

  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "tlkm" } });

  expect(bodyRows()).toHaveLength(1);
  expect(within(bodyRows()[0]).getByText("TLKM")).toBeInTheDocument();
});

test("narrows the table when a side chip is pressed", () => {
  render(
    <TransactionExplorer
      items={[tx({ id: "a", side: "buy" }), tx({ id: "b", side: "sell" })]}
    />,
  );

  const group = screen.getByRole("group", { name: "Jenis" });
  fireEvent.click(within(group).getByRole("button", { name: "Jual" }));

  expect(bodyRows()).toHaveLength(1);
});

test("re-orders the table when a column header is clicked", () => {
  render(
    <TransactionExplorer
      items={[
        tx({ id: "a", ticker: "TLKM.JK", quantity: 10 }),
        tx({ id: "b", ticker: "BBCA.JK", quantity: 20 }),
      ]}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: /Saham/ }));

  expect(within(bodyRows()[0]).getByText("TLKM")).toBeInTheDocument();
});

test("shows one page at a time and steps to the next", () => {
  render(<TransactionExplorer items={many(30)} />);

  expect(bodyRows()).toHaveLength(25);

  fireEvent.click(screen.getByRole("button", { name: /Berikutnya/ }));

  expect(bodyRows()).toHaveLength(5);
});

test("returns to the first page when the filter changes", () => {
  render(<TransactionExplorer items={many(30)} />);

  fireEvent.click(screen.getByRole("button", { name: /Berikutnya/ }));
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "T0" } });

  expect(screen.getByRole("button", { name: /Sebelumnya/ })).toBeDisabled();
});

test("resizes the page when a new page size is chosen", () => {
  render(<TransactionExplorer items={many(30)} />);

  fireEvent.change(screen.getByLabelText(/Baris per halaman/), { target: { value: "50" } });

  expect(bodyRows()).toHaveLength(30);
});

test("summarises only the rows left after filtering", () => {
  render(
    <TransactionExplorer
      items={[
        tx({ id: "a", side: "buy", quantity: 100, price: 9_000 }),
        tx({ id: "b", side: "buy", quantity: 100, price: 1_000, ticker: "TLKM.JK" }),
      ]}
    />,
  );

  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "tlkm" } });

  const summary = screen.getByRole("group", { name: "Ringkasan transaksi" });
  expect(within(summary).getByText("Rp 100.000")).toBeInTheDocument();
  expect(within(summary).queryByText("Rp 900.000")).not.toBeInTheDocument();
});

test("explains an empty result and clears the filter on demand", () => {
  render(<TransactionExplorer items={[tx({ id: "a", ticker: "BBCA.JK" })]} />);

  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "zzzz" } });
  expect(screen.getByText("Tidak Ada Hasil")).toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /Hapus semua filter/ }));

  expect(bodyRows()).toHaveLength(1);
});
