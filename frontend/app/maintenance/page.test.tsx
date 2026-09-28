import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MaintenancePage from "./page";

describe("MaintenancePage", () => {
  it("explains that Astalink is temporarily unavailable", () => {
    render(<MaintenancePage />);

    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "AstaLink sedang dalam pemeliharaan.",
      }),
    ).toBeInTheDocument();
  });

  it("directs the user to AstaLabs on Instagram", () => {
    render(<MaintenancePage />);

    expect(screen.getByRole("link", { name: "AstaLabs.id" })).toHaveAttribute(
      "href",
      "https://www.instagram.com/astalabs.id?stkn=MXVpeXJscDg0YzNjcg%3D%3D",
    );
  });
});
