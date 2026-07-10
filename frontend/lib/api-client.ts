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

export interface AuditSummary {
  audit_id: string;
  intent: string | null;
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface AuditDetail {
  audit_id: string;
  status: string;
  intent: string | null;
  workspace_id: string;
  created_at: string;
  completed_at: string | null;
  allocation_plan: {
    weights: { ticker: string; weight: number }[];
    cash: number;
    cash_buffer: number;
    narration: string;
    relaxations_applied: string[];
  } | null;
  legal_status: string | null;
  legal_citations: { source: string; pasal: string; ayat: string | null; span: string }[];
  transactions: {
    ticker: string;
    side: string;
    quantity: number;
    status: string;
    broker_ref: string | null;
  }[];
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

export interface NewsArticle {
  title: string;
  source: string;
  published_at: string;
  sentiment: "positive" | "neutral" | "negative";
}

export interface NewsResponse {
  ticker: string;
  articles: NewsArticle[];
}

export interface Workspace {
  id: string;
  name: string;
  type: "personal" | "business";
  cash_balance: number;
}

export const LAST_BUSINESS_KEY = "astalink_last_business_id";

export interface Business {
  id: string;
  name: string;
  industry: string | null;
  description: string | null;
  created_at: string;
}

export interface FinancialRecord {
  id: string;
  period_year: number;
  aset: number;
  omset: number;
  profit: number;
}

export interface BusinessDetail extends Business {
  financial_records: FinancialRecord[];
}

export interface RegulationDoc {
  id: string;
  source: string;
  title: string;
  version: string | null;
  indexed_at: string;
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
  listAudit: (workspaceId: string, token: string) =>
    jsonFetch<{ audits: AuditSummary[] }>(
      `/api/v1/audit?workspace_id=${workspaceId}`, { method: "GET" }, token,
    ),
  getAudit: (auditId: string, token: string) =>
    jsonFetch<AuditDetail>(`/api/v1/audit/${auditId}`, { method: "GET" }, token),
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
  getNews: (ticker: string): Promise<NewsResponse> =>
    jsonFetch<NewsResponse>(
      `/api/v1/market/news?ticker=${ticker}`,
      { method: "GET" },
    ),
  chat: (
    body: { message: string; workspace_id: string; thread_id?: string },
    token: string,
  ): Promise<{ message: string; thread_id: string }> =>
    jsonFetch<{ message: string; thread_id: string }>(
      "/api/v1/chat/",
      { method: "POST", body: JSON.stringify(body) },
      token,
    ),

  forgotPassword: (body: { email: string }): Promise<{ message: string }> =>
    jsonFetch<{ message: string }>(
      "/api/v1/auth/forgot-password",
      { method: "POST", body: JSON.stringify(body) },
    ),

  getMe: (token: string): Promise<{ email: string; is_admin: boolean }> =>
    jsonFetch<{ email: string; is_admin: boolean }>(
      "/api/v1/auth/me", { method: "GET" }, token,
    ),

  signup: (body: { email: string; password: string }): Promise<{ message: string }> =>
    jsonFetch<{ message: string }>(
      "/api/v1/auth/signup",
      { method: "POST", body: JSON.stringify(body) },
    ),

  createWorkspace: (
    body: { name: string; type: "personal" | "business" },
    token: string,
  ): Promise<Workspace> =>
    jsonFetch<Workspace>(
      "/api/v1/workspaces",
      { method: "POST", body: JSON.stringify(body) },
      token,
    ),

  listBusinesses: (workspaceId: string, token: string): Promise<Business[]> =>
    jsonFetch<Business[]>(
      `/api/v1/business?workspace_id=${workspaceId}`, { method: "GET" }, token,
    ),

  createBusiness: (
    body: { name: string; workspace_id: string; industry?: string; description?: string },
    token: string,
  ): Promise<Business> =>
    jsonFetch<Business>(
      "/api/v1/business",
      { method: "POST", body: JSON.stringify(body) },
      token,
    ),

  getBusiness: (businessId: string, token: string): Promise<BusinessDetail> =>
    jsonFetch<BusinessDetail>(`/api/v1/business/${businessId}`, { method: "GET" }, token),

  addFinancialRecord: (
    businessId: string,
    body: { period_year: number; aset: number; omset: number; profit: number },
    token: string,
  ): Promise<FinancialRecord> =>
    jsonFetch<FinancialRecord>(
      `/api/v1/business/${businessId}/financials`,
      { method: "POST", body: JSON.stringify(body) },
      token,
    ),

  listLegalDocs: (token: string): Promise<RegulationDoc[]> =>
    jsonFetch<RegulationDoc[]>("/api/v1/legal/documents", { method: "GET" }, token),

  uploadLegalDoc: async (
    file: File,
    source: string,
    title: string,
    token: string,
  ): Promise<RegulationDoc> => {
    const form = new FormData();
    form.append("file", file);
    form.append("source", source);
    form.append("title", title);
    const res = await fetch(`${BACKEND}/api/v1/legal/documents/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
    return res.json() as Promise<RegulationDoc>;
  },
};
