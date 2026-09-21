import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { TransactionPagination } from "./transaction-pagination";

function renderPagination(props: Partial<React.ComponentProps<typeof TransactionPagination>> = {}) {
  const onPageChange = vi.fn();
  const onPageSizeChange = vi.fn();
  render(
    <TransactionPagination
      page={1}
      pageSize={25}
      total={137}
      onPageChange={onPageChange}
      onPageSizeChange={onPageSizeChange}
      {...props}
    />,
  );
  return { onPageChange, onPageSizeChange };
}

test("describes which slice of the ledger is on screen", () => {
  renderPagination({ page: 2 });

  expect(screen.getByText(/Menampilkan 26–50 dari 137/)).toBeInTheDocument();
});

test("stops the range at the last row on a short final page", () => {
  renderPagination({ page: 6 });

  expect(screen.getByText(/Menampilkan 126–137 dari 137/)).toBeInTheDocument();
});

test("reads as zero rows when the filter matched nothing", () => {
  renderPagination({ total: 0 });

  expect(screen.getByText(/Menampilkan 0 dari 0/)).toBeInTheDocument();
});

test("blocks going back from the first page", () => {
  renderPagination({ page: 1 });

  expect(screen.getByRole("button", { name: /Sebelumnya/ })).toBeDisabled();
});

test("blocks going forward from the last page", () => {
  renderPagination({ page: 6 });

  expect(screen.getByRole("button", { name: /Berikutnya/ })).toBeDisabled();
});

test("steps forward one page at a time", () => {
  const { onPageChange } = renderPagination({ page: 2 });

  fireEvent.click(screen.getByRole("button", { name: /Berikutnya/ }));

  expect(onPageChange).toHaveBeenCalledWith(3);
});

test("steps back one page at a time", () => {
  const { onPageChange } = renderPagination({ page: 2 });

  fireEvent.click(screen.getByRole("button", { name: /Sebelumnya/ }));

  expect(onPageChange).toHaveBeenCalledWith(1);
});

test("hands a new page size up to the parent as a number", () => {
  const { onPageSizeChange } = renderPagination();

  fireEvent.change(screen.getByLabelText(/Baris per halaman/), { target: { value: "100" } });

  expect(onPageSizeChange).toHaveBeenCalledWith(100);
});
