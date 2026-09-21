import { describe, expect, it } from "vitest";

import {
  MOBILE_TABS,
  isJourneyRouteActive,
  visibleDesktopSections,
} from "./journey-navigation";

describe("journey navigation", () => {
  it("activates nested route families", () => {
    expect(
      isJourneyRouteActive("/business/abc", ["/transactions", "/business"]),
    ).toBe(true);
    expect(isJourneyRouteActive("/allocation/intake/abc", ["/allocation"])).toBe(
      true,
    );
    expect(
      isJourneyRouteActive("/approvals/a1", ["/portfolio", "/approvals"]),
    ).toBe(true);
  });

  it("does not confuse similarly-prefixed routes", () => {
    expect(isJourneyRouteActive("/portfolio-old", ["/portfolio"])).toBe(false);
  });

  it("keeps exactly five mobile journey stages", () => {
    expect(MOBILE_TABS.map((tab) => tab.label)).toEqual([
      "Beranda",
      "Catat",
      "Rencana",
      "Jelajah",
      "Portofolio",
    ]);
  });

  it("hides regulatory documents from non-admin users", () => {
    expect(JSON.stringify(visibleDesktopSections(false))).not.toContain(
      "/legal-docs",
    );
    expect(JSON.stringify(visibleDesktopSections(true))).toContain("/legal-docs");
  });
});
