const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export interface ApprovalSummary {
  audit_id: string;
  intent: string | null;
  status: string;
  created_at: string;
  workspace_id: string;
}

export interface ApprovalDetail {
  audit_id: string;
  status: string;
  intent: string | null;
  workspace_id: string;
  plan_json: {
    weights: { ticker: string; weight: number }[];
    cash: number;
    cash_buffer: number;
    narration: string;
    relaxations_applied: string[];
  } | null;
  legal_status: string | null;
  legal_citations: { source: string; pasal: string; ayat: string | null; span: string }[];
}

export interface AgentRunRequest {
  message: string;
  workspace_id: string;
  thread_id?: string;
}

export interface AgentRunResponse {
  audit_id: string;
  thread_id: string;
  intent: string | null;
  legal_status: string | null;
  user_approval: string | null;
  allocation_plan: {
    weights: { ticker: string; weight: number }[];
    cash: number;
    cash_buffer: number;
    narration: string;
    relaxations_applied: string[];
  } | null;
  transactions: Record<string, unknown>[];
  revision_count: number;
  messages: { type: string; content: string }[];
  errors: { node: string; reason: string }[];
}

export interface PricePoint {
  date: string;
  close: number;
  sma20: number | null;
  ema50: number | null;
  rsi14: number | null;
}

export interface TickerChartData {
  ticker: string;
  last_close: number | null;
  prev_close: number | null;
  price_change_pct: number | null;
  rsi14: number | null;
  sma20: number | null;
  macd: number | null;
  bb_upper: number | null;
  bb_lower: number | null;
  price_series: PricePoint[];
}

async function jsonFetch<T>(path: string, init?: RequestInit, accessToken?: string): Promise<T> {
  const res = await fetch(`${BACKEND}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  listApprovals: (workspaceId: string, token: string) =>
    jsonFetch<{ approvals: ApprovalSummary[] }>(
      `/api/v1/approvals?workspace_id=${workspaceId}`, { method: "GET" }, token,
    ),
  getApproval: (auditId: string, token: string) =>
    jsonFetch<ApprovalDetail>(`/api/v1/approvals/${auditId}`, { method: "GET" }, token),
  approve: (auditId: string, pin: string, token: string) =>
    jsonFetch<{ audit_id: string; transactions: unknown[] }>(
      `/api/v1/approvals/${auditId}/approve`,
      { method: "POST", body: JSON.stringify({ pin }) },
      token,
    ),
  reject: (auditId: string, reason: string, token: string) =>
    jsonFetch<{ audit_id: string }>(
      `/api/v1/approvals/${auditId}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) },
      token,
    ),
  setPin: (pin: string, token: string) =>
    jsonFetch<void>(`/api/v1/users/me/pin`,
      { method: "POST", body: JSON.stringify({ pin }) }, token),
  runAgent: (body: AgentRunRequest, token: string) =>
    jsonFetch<AgentRunResponse>(
      "/api/v1/agent/run",
      { method: "POST", body: JSON.stringify(body) },
      token,
    ),
  getWatchlist: (tickers: string[]): Promise<TickerChartData[]> =>
    jsonFetch<TickerChartData[]>(
      `/api/v1/market/watchlist?tickers=${tickers.join(",")}`,
      { method: "GET" },
    ),
};
