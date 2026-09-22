import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { AllocationBuyModal } from "./allocation-buy-modal";

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: "test-token" } },
      }),
    },
  }),
}));

vi.mock("@/lib/api-client", () => ({
  api: {
    getPortfolio: vi.fn().mockResolvedValue({ cash_balance: 100_000_000 }),
  },
}));

test("renders PIN confirmation above the allocation dialog", async () => {
  render(
    <AllocationBuyModal
      workspaceId="workspace-1"
      suggestedTickers={[]}
      onClose={() => {}}
      onSuccess={() => {}}
    />,
  );

  const allocate = await screen.findByRole("button", {
    name: /alokasikan dana/i,
  });
  await waitFor(() => expect(allocate).toBeEnabled());

  fireEvent.click(allocate);

  const pinDialog = await screen.findByRole("dialog", {
    name: /konfirmasi pin/i,
  });
  expect(pinDialog.closest("[data-base-ui-portal]")).not.toBeNull();
  expect(pinDialog).toHaveClass("z-[60]");
});

test("enables purchase confirmation after a valid PIN is entered", async () => {
  render(
    <AllocationBuyModal
      workspaceId="workspace-1"
      suggestedTickers={[]}
      onClose={() => {}}
      onSuccess={() => {}}
    />,
  );

  const allocate = await screen.findByRole("button", {
    name: /alokasikan dana/i,
  });
  await waitFor(() => expect(allocate).toBeEnabled());
  fireEvent.click(allocate);

  fireEvent.change(await screen.findByLabelText(/pin keamanan/i), {
    target: { value: "123456" },
  });

  expect(screen.getByRole("button", { name: /setujui/i })).toBeEnabled();
});

test("closes only the PIN confirmation when Escape is pressed", async () => {
  render(
    <AllocationBuyModal
      workspaceId="workspace-1"
      suggestedTickers={[]}
      onClose={() => {}}
      onSuccess={() => {}}
    />,
  );

  const allocate = await screen.findByRole("button", {
    name: /alokasikan dana/i,
  });
  await waitFor(() => expect(allocate).toBeEnabled());
  fireEvent.click(allocate);

  const pinDialog = await screen.findByRole("dialog", {
    name: /konfirmasi pin/i,
  });
  fireEvent.keyDown(pinDialog, { key: "Escape" });

  await waitFor(() => {
    expect(
      screen.queryByRole("dialog", { name: /konfirmasi pin/i }),
    ).not.toBeInTheDocument();
  });
  expect(
    screen.getByRole("dialog", { name: /alokasikan dana ke portofolio/i }),
  ).toBeInTheDocument();
});
