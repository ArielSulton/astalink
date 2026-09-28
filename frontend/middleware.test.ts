// @vitest-environment node

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { middleware } from "./middleware";

vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({
    auth: {
      getUser: async () => ({ data: { user: null } }),
    },
  }),
}));

const originalMaintenanceMode = process.env.MAINTENANCE_MODE;

afterEach(() => {
  if (originalMaintenanceMode === undefined) {
    delete process.env.MAINTENANCE_MODE;
  } else {
    process.env.MAINTENANCE_MODE = originalMaintenanceMode;
  }
});

describe("maintenance mode middleware", () => {
  it("redirects application pages to maintenance before authentication", async () => {
    process.env.MAINTENANCE_MODE = "true";

    const response = await middleware(
      new NextRequest("https://astalink.id/dashboard"),
    );

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "https://astalink.id/maintenance",
    );
  });

  it("allows the maintenance page while maintenance mode is active", async () => {
    process.env.MAINTENANCE_MODE = "true";

    const response = await middleware(
      new NextRequest("https://astalink.id/maintenance"),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("x-middleware-next")).toBe("1");
  });

  it("returns the maintenance URL to the homepage after maintenance", async () => {
    process.env.MAINTENANCE_MODE = "false";

    const response = await middleware(
      new NextRequest("https://astalink.id/maintenance"),
    );

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("https://astalink.id/");
  });
});
