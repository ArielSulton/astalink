import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { MarketTerminal } from "./market-terminal";

vi.mock("@/components/workspace-context", () => ({
  useWorkspace: () => ({ workspaceId: null }),
}));
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { getSession: async () => ({ data: { session: null } }) },
  }),
}));

test("offers a labeled mobile watchlist control and keeps the chart landmark", () => {
  render(<MarketTerminal />);
  expect(
    screen.getByRole("button", { name: /buka daftar saham/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole("main", { name: /grafik pasar/i })).toBeInTheDocument();
});
