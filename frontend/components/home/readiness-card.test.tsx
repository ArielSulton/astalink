import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import type { JourneyHomeResponse } from "@/lib/api-client";

import { ReadinessCard } from "./readiness-card";

function summary(
  overrides: Partial<JourneyHomeResponse["readiness_summary"]> = {},
): JourneyHomeResponse["readiness_summary"] {
  return {
    status: "needs_input",
    decisive_gaps: [],
    blocker_codes: [],
    continuation_href: "/allocation/investor",
    ...overrides,
  } as JourneyHomeResponse["readiness_summary"];
}

test("labels every decisive gap the projection can emit", () => {
  const warn = vi.spyOn(console, "error").mockImplementation(() => {});

  render(
    <ReadinessCard
      summary={summary({
        decisive_gaps: [
          "monthly_expenses",
          "emergency_fund",
          "capital_is_borrowed",
          "horizon_months",
        ],
      })}
      onRetry={() => {}}
    />,
  );

  // A new profile leaves all four blank; none may fall back to the shared text,
  // which previously collapsed them into duplicate React keys.
  expect(screen.queryByText(/informasi kesiapan tambahan/i)).toBeNull();
  expect(warn).not.toHaveBeenCalled();
});

test("keeps list keys unique when labels repeat", () => {
  const warn = vi.spyOn(console, "error").mockImplementation(() => {});

  render(
    <ReadinessCard
      summary={summary({ decisive_gaps: ["unknown_one", "unknown_two"] })}
      onRetry={() => {}}
    />,
  );

  expect(warn).not.toHaveBeenCalled();
});
