import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { SidebarProvider } from "@/components/ui/sidebar";

import { NavUser } from "./nav-user";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getUser: async () => ({ data: { user: { email: "a@b.c" } } }),
      signOut: async () => ({ error: null }),
    },
  }),
}));

function renderHeaderVariant(isAdmin = false) {
  return render(
    <SidebarProvider>
      <NavUser variant="header" isAdmin={isAdmin} />
    </SidebarProvider>,
  );
}

test("exposes an account control with an accessible name", () => {
  renderHeaderVariant();

  // Mobile has no sidebar trigger, so this button is the only way to reach
  // Pengaturan and Keluar on a phone.
  const trigger = screen.getByRole("button", { name: /menu akun/i });
  expect(trigger).toBeInTheDocument();
});

test("keeps the account control at a 44px touch target", () => {
  renderHeaderVariant();

  const trigger = screen.getByRole("button", { name: /menu akun/i });
  expect(trigger.className).toContain("size-11");
});
