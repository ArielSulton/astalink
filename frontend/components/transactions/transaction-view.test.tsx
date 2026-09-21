import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { TransactionView } from "./transaction-view";

test("renders transaction semantics in table and card views", () => {
  render(
    <TransactionView
      items={[
        {
          id: "t1",
          ticker: "BBCA",
          side: "buy",
          quantity: 100,
          price: 9000,
          status: "filled",
          broker_ref: null,
          created_at: "2026-09-20T03:30:00Z",
        },
      ]}
    />,
  );

  expect(screen.getAllByText("BBCA")).toHaveLength(2);
  expect(screen.getAllByText(/Rp 900.000/)).toHaveLength(2);
});
