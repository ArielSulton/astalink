import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { HoldingsView } from "./holdings-view";

test("keeps unavailable prices explicit in both layouts", () => {
  render(
    <HoldingsView
      holdings={[
        {
          ticker: "BBCA",
          quantity: 100,
          avg_cost: 9000,
          cost_basis: 900000,
          last_price: null,
          market_value: null,
          unrealized_pnl: null,
          unrealized_pnl_pct: null,
        },
      ]}
      onBuy={() => {}}
      onSell={() => {}}
      totalEquity={null}
    />,
  );

  expect(screen.getAllByText("—").length).toBeGreaterThan(1);
  expect(screen.queryByText("Rp 0")).not.toBeInTheDocument();
});
