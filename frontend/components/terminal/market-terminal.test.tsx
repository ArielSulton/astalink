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

test("renders the market terminal heading", () => {
  render(<MarketTerminal />);
  expect(screen.getByText(/pasar/i)).toBeInTheDocument();
});
