import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { TransactionSummaryCards } from "./transaction-summary";

test("reports the totals of the rows currently in view", () => {
  render(
    <TransactionSummaryCards
      summary={{ count: 12, totalBuy: 900_000, totalSell: 200_000, netPnl: 150_000 }}
      filtered={false}
    />,
  );

  expect(screen.getByText("12")).toBeInTheDocument();
  expect(screen.getByText("Rp 900.000")).toBeInTheDocument();
  expect(screen.getByText("Rp 200.000")).toBeInTheDocument();
  expect(screen.getByText("+Rp 150.000")).toBeInTheDocument();
});

test("keeps the minus sign on a losing ledger", () => {
  render(
    <TransactionSummaryCards
      summary={{ count: 1, totalBuy: 0, totalSell: 0, netPnl: -75_000 }}
      filtered={false}
    />,
  );

  expect(screen.getByText("-Rp 75.000")).toBeInTheDocument();
});

test("says the numbers cover the filtered subset once a filter is on", () => {
  render(
    <TransactionSummaryCards
      summary={{ count: 3, totalBuy: 0, totalSell: 0, netPnl: 0 }}
      filtered
    />,
  );

  expect(screen.getByText(/hasil filter/i)).toBeInTheDocument();
});
