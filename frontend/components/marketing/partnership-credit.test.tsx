import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { PartnershipCredit } from "./partnership-credit";

test("renders Aeterna Foundation as the credited partner", () => {
  render(<PartnershipCredit />);

  expect(screen.getByText("Berkolaborasi dengan")).toBeInTheDocument();
  expect(screen.getByText("Aeterna Foundation")).toBeInTheDocument();
  expect(
    screen.getByRole("img", { name: "Logo Aeterna Foundation" }),
  ).toHaveAttribute("src", expect.stringContaining("aeterna-foundation.png"));
});
