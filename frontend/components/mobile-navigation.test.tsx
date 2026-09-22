import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { MobileNavigation } from "./mobile-navigation";

vi.mock("next/navigation", () => ({
  usePathname: () => "/allocation/intake/biz-1",
}));

test("renders five stages and a separate Asta action", () => {
  render(<MobileNavigation pendingApprovals={0} />);
  expect(
    screen.getAllByRole("link").filter((node) => node.closest("nav")),
  ).toHaveLength(5);
  expect(screen.getByRole("link", { name: "Tanya Asta" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Rencana" })).toHaveAttribute(
    "aria-current",
    "page",
  );
});

test("pins navigation and Asta above the safe area", () => {
  const { container } = render(<MobileNavigation pendingApprovals={0} />);
  expect(container.querySelector("nav")).toHaveClass(
    "fixed",
    "bottom-0",
    "lg:hidden",
  );
  expect(screen.getByRole("link", { name: "Tanya Asta" }).className).toContain(
    "env(safe-area-inset-bottom)",
  );
});
