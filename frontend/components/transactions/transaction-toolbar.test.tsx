import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { DEFAULT_FILTERS, type TransactionFilters } from "@/lib/transactions/filter";

import { TransactionToolbar } from "./transaction-toolbar";

function renderToolbar(filters: TransactionFilters = DEFAULT_FILTERS) {
  const onFiltersChange = vi.fn();
  render(<TransactionToolbar filters={filters} onFiltersChange={onFiltersChange} />);
  return onFiltersChange;
}

test("hands the typed query up to the parent", () => {
  const onFiltersChange = renderToolbar();

  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "bbca" } });

  expect(onFiltersChange).toHaveBeenCalledWith({ ...DEFAULT_FILTERS, query: "bbca" });
});

test("switches the side filter when its chip is pressed", () => {
  const onFiltersChange = renderToolbar();

  const group = screen.getByRole("group", { name: "Jenis" });
  fireEvent.click(within(group).getByRole("button", { name: "Jual" }));

  expect(onFiltersChange).toHaveBeenCalledWith({ ...DEFAULT_FILTERS, side: "sell" });
});

test("switches the status filter without disturbing the others", () => {
  const onFiltersChange = renderToolbar({ ...DEFAULT_FILTERS, side: "buy" });

  const group = screen.getByRole("group", { name: "Status" });
  fireEvent.click(within(group).getByRole("button", { name: "Gagal" }));

  expect(onFiltersChange).toHaveBeenCalledWith({
    ...DEFAULT_FILTERS,
    side: "buy",
    status: "failed",
  });
});

test("switches the date range when its chip is pressed", () => {
  const onFiltersChange = renderToolbar();

  const group = screen.getByRole("group", { name: "Rentang Waktu" });
  fireEvent.click(within(group).getByRole("button", { name: "30 Hari" }));

  expect(onFiltersChange).toHaveBeenCalledWith({ ...DEFAULT_FILTERS, range: "30d" });
});

test("marks the selected chip as pressed", () => {
  renderToolbar({ ...DEFAULT_FILTERS, side: "sell" });

  const group = screen.getByRole("group", { name: "Jenis" });
  expect(within(group).getByRole("button", { name: "Jual" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(within(group).getByRole("button", { name: "Semua" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
});

test("offers no reset while the view is unfiltered", () => {
  renderToolbar();

  expect(screen.queryByRole("button", { name: /Reset/ })).not.toBeInTheDocument();
});

test("clears every filter at once when reset is pressed", () => {
  const onFiltersChange = renderToolbar({ query: "bbca", side: "sell", status: "failed", range: "7d" });

  fireEvent.click(screen.getByRole("button", { name: /Reset/ }));

  expect(onFiltersChange).toHaveBeenCalledWith(DEFAULT_FILTERS);
});
