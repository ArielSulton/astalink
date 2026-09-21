import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { api } from "@/lib/api-client";

import { HomePage } from "./home-page";

vi.mock("@/components/workspace-context", () => ({
  useWorkspace: vi.fn(),
}));
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getSession: async () => ({
        data: { session: { access_token: "x" } },
      }),
    },
  }),
}));

afterEach(() => {
  vi.restoreAllMocks();
});

test("does not request home without a workspace", async () => {
  const { useWorkspace } = await import("@/components/workspace-context");
  vi.mocked(useWorkspace).mockReturnValue({ workspaceId: null } as never);
  const spy = vi.spyOn(api, "getJourneyHome");

  render(<HomePage />);

  expect(screen.getByText(/pilih workspace/i)).toBeInTheDocument();
  expect(spy).not.toHaveBeenCalled();
});

test("renders a failed section without turning it into zero", async () => {
  const { useWorkspace } = await import("@/components/workspace-context");
  vi.mocked(useWorkspace).mockReturnValue({ workspaceId: "ws-1" } as never);
  vi.spyOn(api, "getJourneyHome").mockResolvedValue({
    workspace_id: "ws-1",
    workspace_name: "Personal",
    workspace_type: "personal",
    generated_at: "2026-09-20T03:30:00Z",
    financial_snapshot: [
      {
        key: "portfolio_value",
        label: "Portofolio sandbox",
        value: null,
        unit: "IDR",
        state: "error",
        as_of: null,
        source: "portfolio",
        change_text: null,
      },
    ],
    readiness_summary: {
      status: "unavailable",
      decisive_gaps: [],
      blocker_codes: [],
      continuation_href: "/allocation",
    },
    next_action: {
      kind: "ask_asta",
      title: "Mulai",
      rationale: "Mulai",
      href: "/chatbot",
      rule_id: "fallback",
    },
    allocation_preview: null,
    recent_activity: [],
    pending_approvals_count: 0,
    section_health: {
      portfolio: {
        state: "error",
        message: "Bagian ini belum dapat diperbarui.",
      },
    },
  });

  render(<HomePage />);

  await waitFor(() =>
    expect(screen.getByText(/belum dapat diperbarui/i)).toBeInTheDocument(),
  );
  expect(screen.queryByText("Rp 0")).not.toBeInTheDocument();
});
