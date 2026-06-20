# Dashboard Pages Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill the four placeholder dashboard pages (External News, Chatbot, Asset View, Legal Document) with functional content.

**Architecture:** External News and Chatbot are thin lifts — backend logic already exists, work is frontend UI + minimal API wiring. Asset View uses existing approvals endpoints (no new backend). Legal Docs adds list + PDF-upload endpoints to `legal.py` and a two-section frontend.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript strict, Tailwind v4, FastAPI, Supabase (service-role client), pypdf, rank_bm25, lucide-react

## Global Constraints

- Dark palette — `bg-[#0a0b0d]` page bg, `bg-[#16181c]` card, `border-[#2a2d36]` border, `text-[#a8acb3]` muted, `text-[#0052ff]` primary blue, `#05b169` positive, `#cf202f` negative/rejected
- Every client component has `"use client"` at line 1
- Auth token: `const sb = createClient(); const { data: { session } } = await sb.auth.getSession();` then `session.access_token` — same pattern as `frontend/app/(protected)/approvals/page.tsx`
- `frontend/lib/api-client.ts`: new methods inside the `api` object before the closing `};`; use **arrow-function** style (not method shorthand) — matches all existing entries
- `npx tsc --noEmit` must pass zero errors after each task
- Backend tests run with `cd backend && python -m pytest <test_file> -v` using the Docker venv; mock network calls with `unittest.mock.patch`
- Commit after each task

---

## File Map

| Task | Creates / Modifies |
|------|--------------------|
| 1 | `backend/app/api/v1/market.py` (modify), `backend/tests/test_news_endpoint.py` (create) |
| 2 | `frontend/app/(protected)/news/page.tsx` (rewrite), `frontend/lib/api-client.ts` (modify) |
| 3 | `frontend/app/(protected)/chatbot/page.tsx` (rewrite), `frontend/lib/api-client.ts` (modify) |
| 4 | `frontend/app/(protected)/assets/page.tsx` (rewrite) |
| 5 | `backend/app/api/v1/legal.py` (modify), `backend/pyproject.toml` (modify), `backend/tests/test_legal_docs.py` (create) |
| 6 | `frontend/app/(protected)/legal-docs/page.tsx` (rewrite), `frontend/lib/api-client.ts` (modify) |

---

### Task 1: External News backend endpoint

**Files:**
- Modify: `backend/app/api/v1/market.py`
- Create: `backend/tests/test_news_endpoint.py`

**Interfaces:**
- Consumes: `fetch_news(ticker: str, max_items: int = 5) -> list[NewsItem]` from `app.agents.market.news_client` (sync — must wrap with `asyncio.to_thread`)
- Consumes: `NewsItem` from `app.agents.market.schemas` — fields: `title: str`, `source: str`, `published_at: str`, `sentiment: Literal["positive","neutral","negative"]`
- Produces: `GET /api/v1/market/news?ticker=BBCA.JK` → `{"ticker": "BBCA.JK", "articles": [...]}`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_news_endpoint.py
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.agents.market.schemas import NewsItem

client = TestClient(app)

MOCK_ARTICLES = [
    NewsItem(title="BBCA posts record profit", source="Reuters",
             published_at="2026-06-20T10:00:00Z", sentiment="positive"),
    NewsItem(title="IDX market steady", source="Bloomberg",
             published_at="2026-06-20T09:00:00Z", sentiment="neutral"),
]

def test_news_returns_structure():
    with patch("app.api.v1.market.fetch_news", return_value=MOCK_ARTICLES):
        resp = client.get("/api/v1/market/news?ticker=BBCA.JK")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "BBCA.JK"
    assert len(data["articles"]) == 2
    assert data["articles"][0]["sentiment"] == "positive"

def test_news_empty_when_key_missing():
    with patch("app.api.v1.market.fetch_news", return_value=[]):
        resp = client.get("/api/v1/market/news?ticker=TLKM.JK")
    assert resp.status_code == 200
    assert resp.json()["articles"] == []
    assert resp.json()["ticker"] == "TLKM.JK"
```

- [ ] **Step 2: Run test — expect FAIL (404 endpoint not found)**

```bash
cd backend && python -m pytest tests/test_news_endpoint.py -v
```

Expected: `FAILED` — `assert resp.status_code == 200` fails with 404.

- [ ] **Step 3: Add NewsResponse model and endpoint to `market.py`**

At the top of `backend/app/api/v1/market.py`, add the import:
```python
import asyncio
from app.agents.market.news_client import fetch_news
from app.agents.market.schemas import NewsItem
```

Add the `NewsResponse` model right after the existing `TickerChartData` class:
```python
class NewsResponse(BaseModel):
    ticker: str
    articles: list[NewsItem]
```

Add the endpoint at the end of the file (before the last line):
```python
@router.get("/news", response_model=NewsResponse)
async def get_ticker_news(
    ticker: str = Query(default="BBCA.JK", description="Single IDX ticker symbol"),
) -> NewsResponse:
    # fetch_news is sync (uses httpx.get + Gemini) — run in thread pool
    articles = await asyncio.to_thread(fetch_news, ticker, 5)
    return NewsResponse(ticker=ticker, articles=articles)
```

- [ ] **Step 4: Run tests — expect 2/2 PASS**

```bash
cd backend && python -m pytest tests/test_news_endpoint.py -v
```

Expected:
```
PASSED tests/test_news_endpoint.py::test_news_returns_structure
PASSED tests/test_news_endpoint.py::test_news_empty_when_key_missing
2 passed
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/market.py backend/tests/test_news_endpoint.py
git commit -m "feat(news): add GET /api/v1/market/news endpoint"
```

---

### Task 2: External News frontend page

**Files:**
- Modify: `frontend/lib/api-client.ts` (add `NewsArticle`, `NewsResponse` types + `getNews` method)
- Rewrite: `frontend/app/(protected)/news/page.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/market/news?ticker=X` → `NewsResponse` (from Task 1)
- Produces: `api.getNews(ticker: string): Promise<NewsResponse>` for Task 3 (chatbot uses none)

- [ ] **Step 1: Add types and method to `api-client.ts`**

After the `TickerChartData` interface (around line 71), insert:
```typescript
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
```

Inside the `api` object, before the closing `};`, add:
```typescript
  getNews: (ticker: string): Promise<NewsResponse> =>
    jsonFetch<NewsResponse>(
      `/api/v1/market/news?ticker=${ticker}`,
      { method: "GET" },
    ),
```

- [ ] **Step 2: Run tsc — expect zero errors**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no output.

- [ ] **Step 3: Rewrite the news page**

Replace the full content of `frontend/app/(protected)/news/page.tsx`:

```tsx
"use client";
import { useEffect, useState } from "react";
import { Minus, Newspaper, TrendingDown, TrendingUp } from "lucide-react";
import { api, NewsArticle, NewsResponse } from "@/lib/api-client";

const TICKERS = ["BBCA.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"];

const SENTIMENT_ICON: Record<NewsArticle["sentiment"], React.ReactNode> = {
  positive: <TrendingUp className="h-3 w-3" />,
  neutral: <Minus className="h-3 w-3" />,
  negative: <TrendingDown className="h-3 w-3" />,
};

const SENTIMENT_CLASS: Record<NewsArticle["sentiment"], string> = {
  positive: "text-[#05b169] bg-[#05b16915] border-[#05b16930]",
  neutral: "text-[#a8acb3] bg-[#a8acb315] border-[#a8acb330]",
  negative: "text-[#cf202f] bg-[#cf202f15] border-[#cf202f30]",
};

export default function NewsPage() {
  const [selectedTicker, setSelectedTicker] = useState("BBCA.JK");
  const [news, setNews] = useState<NewsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setNews(null);
    api
      .getNews(selectedTicker)
      .then(setNews)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedTicker]);

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      {/* Header + ticker pills */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold text-white flex-1">External News</h1>
        <div className="flex gap-2">
          {TICKERS.map((t) => (
            <button
              key={t}
              onClick={() => setSelectedTicker(t)}
              className={`px-3 py-1 text-xs rounded-full font-mono transition-colors ${
                selectedTicker === t
                  ? "bg-[#0052ff] text-white"
                  : "bg-[#16181c] text-[#a8acb3] border border-[#2a2d36] hover:text-white"
              }`}
            >
              {t.replace(".JK", "")}
            </button>
          ))}
        </div>
      </div>

      {/* Skeletons */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-[88px] rounded-xl bg-[#16181c] animate-pulse border border-[#2a2d36]" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && news && news.articles.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-[#5b616e]">
          <Newspaper className="h-9 w-9" />
          <p className="text-sm text-center">
            Tidak ada berita untuk {selectedTicker.replace(".JK", "")}.
            <br />
            Pastikan <code className="font-mono">NEWS_API_KEY</code> sudah dikonfigurasi di backend.
          </p>
        </div>
      )}

      {/* Article cards */}
      {!loading && news && news.articles.length > 0 && (
        <div className="space-y-3">
          {news.articles.map((article, i) => (
            <article
              key={i}
              className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-4 space-y-2"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm text-white font-medium leading-snug flex-1">
                  {article.title}
                </p>
                <span
                  className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border shrink-0 ${SENTIMENT_CLASS[article.sentiment]}`}
                >
                  {SENTIMENT_ICON[article.sentiment]}
                  {article.sentiment}
                </span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-[#5b616e]">
                <span>{article.source}</span>
                <span>·</span>
                <span>
                  {new Date(article.published_at).toLocaleDateString("id-ID", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tsc — expect zero errors**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api-client.ts "frontend/app/(protected)/news/page.tsx"
git commit -m "feat(news): External News page with sentiment-tagged article cards"
```

---

### Task 3: Chatbot frontend page

**Files:**
- Modify: `frontend/lib/api-client.ts` (add `chat` method)
- Rewrite: `frontend/app/(protected)/chatbot/page.tsx`

**Interfaces:**
- Consumes: `POST /api/v1/chat/` — accepts `{message: string, thread_id?: string}`, returns `{message: string, thread_id: string}`, **requires auth token**
- Thread ID persisted in `localStorage` under key `"astalink_chat_thread_id"`

- [ ] **Step 1: Add `chat` method to `api-client.ts`**

Inside the `api` object, before the closing `};`, add:
```typescript
  chat: (
    body: { message: string; thread_id?: string },
    token: string,
  ): Promise<{ message: string; thread_id: string }> =>
    jsonFetch<{ message: string; thread_id: string }>(
      "/api/v1/chat/",
      { method: "POST", body: JSON.stringify(body) },
      token,
    ),
```

- [ ] **Step 2: Run tsc — expect zero errors**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no output.

- [ ] **Step 3: Rewrite the chatbot page**

Replace the full content of `frontend/app/(protected)/chatbot/page.tsx`:

```tsx
"use client";
import { useEffect, useRef, useState } from "react";
import { Bot, Send } from "lucide-react";
import { api } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const THREAD_KEY = "astalink_chat_thread_id";

export default function ChatbotPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | undefined>(undefined);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem(THREAD_KEY);
    if (saved) setThreadId(saved);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;

    const sb = createClient();
    const {
      data: { session },
    } = await sb.auth.getSession();
    if (!session) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await api.chat(
        { message: text, thread_id: threadId },
        session.access_token,
      );
      setThreadId(res.thread_id);
      localStorage.setItem(THREAD_KEY, res.thread_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.message }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Maaf, terjadi kesalahan. Coba lagi." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function clearThread() {
    localStorage.removeItem(THREAD_KEY);
    setThreadId(undefined);
    setMessages([]);
  }

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 0px)" }}>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e2028] shrink-0">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-[#0052ff]" />
          <span className="text-white font-medium text-sm">Astalink AI</span>
        </div>
        <button
          onClick={clearThread}
          className="text-xs text-[#5b616e] hover:text-[#a8acb3] transition-colors"
        >
          Percakapan baru
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
            <Bot className="h-14 w-14 text-[#2a2d36]" />
            <p className="text-[#5b616e] text-sm max-w-xs">
              Tanya apa saja tentang investasi, regulasi OJK/UUPM, atau kondisi pasar saham IDX.
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[78%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-[#0052ff] text-white rounded-br-sm"
                  : "bg-[#16181c] text-[#dee1e6] border border-[#2a2d36] rounded-bl-sm"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#16181c] border border-[#2a2d36] rounded-2xl rounded-bl-sm px-4 py-3.5">
              <div className="flex gap-1.5 items-center">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-1.5 w-1.5 rounded-full bg-[#a8acb3] animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-[#1e2028] shrink-0">
        <div className="flex gap-2 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Ketik pesan… (Enter untuk kirim, Shift+Enter untuk baris baru)"
            rows={1}
            className="flex-1 resize-none bg-[#16181c] border border-[#2a2d36] rounded-xl px-4 py-3 text-sm text-white placeholder:text-[#5b616e] focus:outline-none focus:border-[#0052ff] transition-colors"
            style={{ maxHeight: "128px" }}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="shrink-0 h-10 w-10 rounded-xl bg-[#0052ff] text-white flex items-center justify-center hover:bg-[#0047db] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tsc — expect zero errors**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api-client.ts "frontend/app/(protected)/chatbot/page.tsx"
git commit -m "feat(chatbot): full chat UI with thread persistence and typing indicator"
```

---

### Task 4: Asset View frontend page

**Files:**
- Rewrite: `frontend/app/(protected)/assets/page.tsx`

**Interfaces:**
- Consumes (already in `api-client.ts`):
  - `api.listApprovals(workspaceId: string, token: string): Promise<{ approvals: ApprovalSummary[] }>`
  - `api.getApproval(auditId: string, token: string): Promise<ApprovalDetail>`
  - `ApprovalDetail.plan_json` = `{ weights: {ticker: string; weight: number}[], cash: number, cash_buffer: number, narration: string, relaxations_applied: string[] } | null`
- Consumes: `WorkspaceSwitcher` from `@/components/workspace-switcher` — props `{ current: string | null; onChange: (id: string) => void }`
- Consumes: `AllocationChart` from `@/components/allocation-chart` — props `{ weights: { ticker: string; weight: number }[] }`

- [ ] **Step 1: Rewrite the assets page**

Replace the full content of `frontend/app/(protected)/assets/page.tsx`:

```tsx
"use client";
import { useEffect, useState } from "react";
import { Briefcase, TrendingUp } from "lucide-react";
import { api, ApprovalDetail } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { AllocationChart } from "@/components/allocation-chart";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";

export default function AssetsPage() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ApprovalDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) {
      setDetail(null);
      return;
    }

    setLoading(true);
    setError(null);

    (async () => {
      try {
        const sb = createClient();
        const {
          data: { session },
        } = await sb.auth.getSession();
        if (!session) return;

        const { approvals } = await api.listApprovals(workspaceId, session.access_token);
        const completed = approvals.filter((a) => a.status === "completed");
        if (!completed.length) {
          setDetail(null);
          return;
        }

        // Most recent completed approval
        const latest = completed[completed.length - 1];
        const d = await api.getApproval(latest.audit_id, session.access_token);
        setDetail(d);
      } catch {
        setError("Gagal memuat data aset.");
      } finally {
        setLoading(false);
      }
    })();
  }, [workspaceId]);

  const weights = detail?.plan_json?.weights ?? [];
  const cash = detail?.plan_json?.cash ?? 0;
  const cashBuffer = detail?.plan_json?.cash_buffer ?? 0;
  const narration = detail?.plan_json?.narration ?? "";

  return (
    <div className="p-6 space-y-5 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-white">Asset View</h1>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>

      {/* No workspace selected */}
      {!workspaceId && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-[#5b616e]">
          <Briefcase className="h-9 w-9" />
          <p className="text-sm">Pilih workspace untuk melihat alokasi aset Anda.</p>
        </div>
      )}

      {/* Loading */}
      {workspaceId && loading && (
        <div className="space-y-3">
          <div className="h-48 rounded-xl bg-[#16181c] animate-pulse border border-[#2a2d36]" />
          <div className="h-20 rounded-xl bg-[#16181c] animate-pulse border border-[#2a2d36]" />
        </div>
      )}

      {/* Error */}
      {workspaceId && !loading && error && (
        <p className="text-sm text-[#cf202f] p-4 rounded-xl border border-[#cf202f30] bg-[#cf202f08]">
          {error}
        </p>
      )}

      {/* No data */}
      {workspaceId && !loading && !error && !detail && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-[#5b616e]">
          <TrendingUp className="h-9 w-9" />
          <p className="text-sm">Belum ada alokasi yang disetujui di workspace ini.</p>
          <p className="text-xs text-[#3a3d46]">Jalankan analisis dari halaman Dashboard terlebih dahulu.</p>
        </div>
      )}

      {/* Portfolio content */}
      {workspaceId && !loading && detail && (
        <div className="space-y-4">
          {/* Legal status badge */}
          <div className="flex items-center gap-2">
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${
                detail.legal_status === "approved"
                  ? "text-[#05b169] bg-[#05b16915] border-[#05b16930]"
                  : detail.legal_status === "partial"
                  ? "text-[#f4b000] bg-[#f4b00015] border-[#f4b00030]"
                  : "text-[#cf202f] bg-[#cf202f15] border-[#cf202f30]"
              }`}
            >
              Legal: {detail.legal_status ?? "—"}
            </span>
          </div>

          {/* Allocation chart */}
          <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-5">
            <h2 className="text-xs font-medium text-[#5b616e] uppercase tracking-wide mb-4">
              Alokasi Portofolio
            </h2>
            {weights.length > 0 ? (
              <AllocationChart weights={weights} />
            ) : (
              <p className="text-sm text-[#5b616e]">Tidak ada alokasi saham.</p>
            )}
          </div>

          {/* Cash positions */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-4">
              <p className="text-xs text-[#5b616e] mb-1">Kas</p>
              <p className="text-2xl font-semibold text-white font-mono">
                {(cash * 100).toFixed(1)}%
              </p>
            </div>
            <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-4">
              <p className="text-xs text-[#5b616e] mb-1">Buffer Kas</p>
              <p className="text-2xl font-semibold text-white font-mono">
                {(cashBuffer * 100).toFixed(1)}%
              </p>
            </div>
          </div>

          {/* AI narration */}
          {narration && (
            <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-5">
              <h2 className="text-xs font-medium text-[#5b616e] uppercase tracking-wide mb-2">
                Analisis AI
              </h2>
              <p className="text-sm text-[#a8acb3] leading-relaxed">{narration}</p>
            </div>
          )}

          {/* Relaxations */}
          {detail.plan_json?.relaxations_applied &&
            detail.plan_json.relaxations_applied.length > 0 && (
              <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-4">
                <p className="text-xs text-[#5b616e] mb-2 uppercase tracking-wide">Relaksasi Diterapkan</p>
                <ul className="space-y-1">
                  {detail.plan_json.relaxations_applied.map((r, i) => (
                    <li key={i} className="text-xs text-[#a8acb3] flex items-center gap-2">
                      <span className="h-1 w-1 rounded-full bg-[#f4b000] shrink-0" />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Run tsc — expect zero errors**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/(protected)/assets/page.tsx"
git commit -m "feat(assets): Asset View page with portfolio allocation and AI narration"
```

---

### Task 5: Legal Docs backend (list + upload endpoints)

**Files:**
- Modify: `backend/pyproject.toml` (add `pypdf`)
- Modify: `backend/app/api/v1/legal.py` (add list + upload endpoints)
- Create: `backend/tests/test_legal_docs.py`

**Interfaces:**
- Consumes: `get_admin_client()` from `app.core.supabase_admin` (service-role Supabase client)
- Consumes: `chunk_regulation_text(text: str, source: str) -> list[Chunk]` from `app.agents.legal.chunker`
- Consumes: `BM25Retriever` from `app.agents.legal.retriever` — methods: `.load(path: Path)`, `.from_chunks(chunks: list[Chunk])`, `.save(path: Path)`
- BM25 path constant (copy from `node.py` line 30): `Path(__file__).parent.parent.parent / "data" / "bm25_index.pkl"` (legal.py is one level shallower than node.py, adjust accordingly)
- Produces:
  - `GET /api/v1/legal/documents` → `list[RegulationDocumentOut]` (no auth — public catalog)
  - `POST /api/v1/legal/documents/upload` → `RegulationDocumentOut` (requires auth)

- [ ] **Step 1: Add `pypdf` to `pyproject.toml`**

In `backend/pyproject.toml`, find the `dependencies` list and add `"pypdf>=4.0.0"` (put it alphabetically near `pydantic`).

- [ ] **Step 2: Install in Docker container**

```bash
docker exec astalink-backend-1 uv pip install pypdf
```

Expected: `Successfully installed pypdf-X.X.X`

- [ ] **Step 3: Write the failing tests**

```python
# backend/tests/test_legal_docs.py
import io
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MOCK_DOCS = [
    {
        "id": "aaaa-1111",
        "source": "OJK",
        "title": "POJK Nomor 3 Tahun 2021",
        "version": "2021",
        "indexed_at": "2026-01-01T00:00:00+00:00",
    }
]


def test_list_documents_returns_list():
    mock_result = MagicMock()
    mock_result.data = MOCK_DOCS
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.order.return_value.execute.return_value = mock_result

    with patch("app.api.v1.legal.get_admin_client", return_value=mock_sb):
        resp = client.get("/api/v1/legal/documents")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["source"] == "OJK"


def test_upload_rejects_non_pdf():
    fake_token = "fake-token"
    mock_user = {"sub": "user-123"}
    with patch("app.api.deps.verify_token", return_value=mock_user):
        resp = client.post(
            "/api/v1/legal/documents/upload",
            files={"file": ("document.txt", b"plain text", "text/plain")},
            data={"source": "user", "title": "Test"},
            headers={"Authorization": f"Bearer {fake_token}"},
        )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]
```

- [ ] **Step 4: Run tests — expect FAIL (endpoints not yet defined)**

```bash
cd backend && python -m pytest tests/test_legal_docs.py -v
```

Expected: `FAILED` — `assert resp.status_code == 200` fails with 404.

- [ ] **Step 5: Add imports and models to `legal.py`**

At the top of `backend/app/api/v1/legal.py`, add to existing imports:
```python
import hashlib
import io
from pathlib import Path

from fastapi import File, UploadFile
from pypdf import PdfReader

from app.agents.legal.chunker import chunk_regulation_text
from app.agents.legal.retriever import BM25Retriever
from app.core.supabase_admin import get_admin_client
```

Add new Pydantic model after the existing `LegalCheckResponse` class:
```python
class RegulationDocumentOut(BaseModel):
    id: str
    source: str
    title: str
    version: str | None = None
    indexed_at: str

# BM25 index path — same directory as node.py's BM25_PATH resolves to:
# backend/data/bm25_index.pkl
_BM25_PATH = Path(__file__).parent.parent.parent.parent / "data" / "bm25_index.pkl"
```

- [ ] **Step 6: Add list endpoint to `legal.py`**

```python
@router.get("/documents", response_model=list[RegulationDocumentOut])
async def list_documents() -> list[RegulationDocumentOut]:
    sb = get_admin_client()
    res = (
        sb.table("regulation_documents")
        .select("id,source,title,version,indexed_at")
        .order("indexed_at", desc=True)
        .execute()
    )
    return [RegulationDocumentOut(**row) for row in (res.data or [])]
```

- [ ] **Step 7: Add upload endpoint to `legal.py`**

```python
@router.post("/documents/upload", response_model=RegulationDocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    source: str = "user",
    title: str = "",
    user: dict = Depends(get_current_user),
) -> RegulationDocumentOut:
    if not (file.filename or "").lower().endswith(".pdf"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    doc_hash = hashlib.sha256(content).hexdigest()

    # Extract text
    reader = PdfReader(io.BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Could not extract text from PDF.")

    # Chunk and update BM25 index
    chunks = chunk_regulation_text(text, source=source or (file.filename or "upload"))
    _BM25_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _BM25_PATH.exists():
        existing = BM25Retriever.load(_BM25_PATH)
        all_chunks = existing._chunks + chunks
    else:
        all_chunks = chunks
    new_retriever = BM25Retriever.from_chunks(all_chunks)
    new_retriever.save(_BM25_PATH)

    # Insert metadata
    sb = get_admin_client()
    row = (
        sb.table("regulation_documents")
        .insert({
            "source": source,
            "title": title or (file.filename or "Uploaded Document"),
            "doc_hash": doc_hash,
            "metadata": {"pages": len(reader.pages), "chunks": len(chunks)},
        })
        .execute()
    )
    inserted = row.data[0]
    return RegulationDocumentOut(**inserted)
```

**Note:** `existing._chunks` accesses the private attribute directly. This is acceptable since `BM25Retriever` is internal code we own.

- [ ] **Step 8: Run tests — expect 2/2 PASS**

```bash
cd backend && python -m pytest tests/test_legal_docs.py -v
```

Expected:
```
PASSED tests/test_legal_docs.py::test_list_documents_returns_list
PASSED tests/test_legal_docs.py::test_upload_rejects_non_pdf
2 passed
```

- [ ] **Step 9: Commit**

```bash
git add backend/pyproject.toml backend/app/api/v1/legal.py backend/tests/test_legal_docs.py
git commit -m "feat(legal-docs): add document list and PDF upload endpoints"
```

---

### Task 6: Legal Docs frontend page

**Files:**
- Modify: `frontend/lib/api-client.ts` (add `listLegalDocs`, `uploadLegalDoc` methods + `RegulationDoc` interface)
- Rewrite: `frontend/app/(protected)/legal-docs/page.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/legal/documents` → `RegulationDocumentOut[]` (no auth)
- Consumes: `POST /api/v1/legal/documents/upload` (multipart form, requires auth)
- Produces: Two-section UI — default docs catalog + PDF upload form

- [ ] **Step 1: Add types and methods to `api-client.ts`**

After the `NewsResponse` interface, insert:
```typescript
export interface RegulationDoc {
  id: string;
  source: string;
  title: string;
  version: string | null;
  indexed_at: string;
}
```

Inside the `api` object, before `};`, add:
```typescript
  listLegalDocs: (): Promise<RegulationDoc[]> =>
    jsonFetch<RegulationDoc[]>("/api/v1/legal/documents", { method: "GET" }),

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
```

**Note:** `uploadLegalDoc` cannot use `jsonFetch` because it sends `multipart/form-data` (no `Content-Type: application/json` header). Use raw `fetch` with `FormData` and no `Content-Type` override — the browser sets it automatically with the correct boundary.

- [ ] **Step 2: Run tsc — expect zero errors**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no output.

- [ ] **Step 3: Rewrite the legal-docs page**

Replace the full content of `frontend/app/(protected)/legal-docs/page.tsx`:

```tsx
"use client";
import { useEffect, useRef, useState } from "react";
import { FileText, Scale, Upload } from "lucide-react";
import { api, RegulationDoc } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

export default function LegalDocsPage() {
  const [docs, setDocs] = useState<RegulationDoc[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadSource, setUploadSource] = useState("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load default docs on mount
  useEffect(() => {
    api
      .listLegalDocs()
      .then(setDocs)
      .catch(() => {})
      .finally(() => setDocsLoading(false));
  }, []);

  async function handleUpload() {
    if (!uploadFile) return;
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(false);

    try {
      const sb = createClient();
      const {
        data: { session },
      } = await sb.auth.getSession();
      if (!session) { setUploadError("Sesi habis, silakan login ulang."); return; }

      const newDoc = await api.uploadLegalDoc(
        uploadFile,
        uploadSource || "user",
        uploadTitle || uploadFile.name,
        session.access_token,
      );
      setDocs((prev) => [newDoc, ...prev]);
      setUploadFile(null);
      setUploadSource("");
      setUploadTitle("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      setUploadSuccess(true);
      setTimeout(() => setUploadSuccess(false), 3000);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Upload gagal.";
      setUploadError(msg);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-xl font-semibold text-white">Legal Document</h1>

      {/* ── Default / indexed docs ─────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="text-xs font-medium text-[#5b616e] uppercase tracking-wide">
          Dokumen Regulasi Terindeks
        </h2>

        {docsLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-14 rounded-xl bg-[#16181c] animate-pulse border border-[#2a2d36]"
              />
            ))}
          </div>
        )}

        {!docsLoading && docs.length === 0 && (
          <div className="flex items-center gap-3 p-4 rounded-xl border border-[#2a2d36] bg-[#16181c] text-[#5b616e]">
            <Scale className="h-5 w-5 shrink-0" />
            <p className="text-sm">
              Belum ada dokumen terindeks. Unggah dokumen pertama di bawah.
            </p>
          </div>
        )}

        {!docsLoading && docs.length > 0 && (
          <div className="space-y-2">
            {docs.map((doc) => (
              <div
                key={doc.id}
                className="flex items-start gap-3 p-3.5 rounded-xl border border-[#2a2d36] bg-[#16181c]"
              >
                <FileText className="h-4 w-4 text-[#0052ff] shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium truncate">{doc.title}</p>
                  <div className="flex items-center gap-2 mt-0.5 text-[11px] text-[#5b616e]">
                    <span className="px-1.5 py-0.5 rounded bg-[#0a0b0d] border border-[#2a2d36] font-mono">
                      {doc.source}
                    </span>
                    {doc.version && <span>{doc.version}</span>}
                    <span>·</span>
                    <span>
                      {new Date(doc.indexed_at).toLocaleDateString("id-ID", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Upload section ─────────────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="text-xs font-medium text-[#5b616e] uppercase tracking-wide">
          Unggah Dokumen Mandiri
        </h2>

        <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-5 space-y-4">
          {/* File picker */}
          <div>
            <label className="text-xs text-[#a8acb3] mb-1.5 block">File PDF</label>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border border-dashed border-[#2a2d36] rounded-xl p-6 flex flex-col items-center gap-2 cursor-pointer hover:border-[#0052ff] transition-colors"
            >
              <Upload className="h-6 w-6 text-[#5b616e]" />
              <p className="text-sm text-[#5b616e]">
                {uploadFile ? uploadFile.name : "Klik untuk pilih file PDF"}
              </p>
              {uploadFile && (
                <p className="text-[11px] text-[#3a3d46]">
                  {(uploadFile.size / 1024).toFixed(0)} KB
                </p>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
            />
          </div>

          {/* Source + Title */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-[#a8acb3] mb-1.5 block">Sumber</label>
              <input
                value={uploadSource}
                onChange={(e) => setUploadSource(e.target.value)}
                placeholder="cth. OJK, UUPM, user"
                className="w-full bg-[#0a0b0d] border border-[#2a2d36] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[#5b616e] focus:outline-none focus:border-[#0052ff] transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-[#a8acb3] mb-1.5 block">Judul</label>
              <input
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                placeholder="Judul dokumen"
                className="w-full bg-[#0a0b0d] border border-[#2a2d36] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[#5b616e] focus:outline-none focus:border-[#0052ff] transition-colors"
              />
            </div>
          </div>

          {/* Feedback */}
          {uploadError && (
            <p className="text-xs text-[#cf202f] p-3 rounded-lg bg-[#cf202f08] border border-[#cf202f30]">
              {uploadError}
            </p>
          )}
          {uploadSuccess && (
            <p className="text-xs text-[#05b169] p-3 rounded-lg bg-[#05b16908] border border-[#05b16930]">
              Dokumen berhasil diunggah dan diindeks ke BM25.
            </p>
          )}

          {/* Submit */}
          <button
            onClick={handleUpload}
            disabled={!uploadFile || uploading}
            className="w-full py-2.5 rounded-lg bg-[#0052ff] text-white text-sm font-medium hover:bg-[#0047db] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? "Mengunggah…" : "Unggah & Indeks"}
          </button>
        </div>
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Run tsc — expect zero errors**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api-client.ts "frontend/app/(protected)/legal-docs/page.tsx"
git commit -m "feat(legal-docs): Legal Document page with doc catalog and PDF upload"
```

---

## Self-Review

**Spec coverage:**
- ✅ Chatbot page — full chat UI, thread persistence, loading state
- ✅ Asset View — workspace selector, portfolio allocation, cash, narration, relaxations
- ✅ Legal Document — indexed docs list + PDF upload with BM25 re-indexing
- ✅ External News — ticker selector, sentiment-tagged article cards, skeleton loading

**Placeholder scan:** No TBD, TODO, or vague steps found. All code blocks are complete.

**Type consistency:**
- `NewsArticle.sentiment` typed as `"positive" | "neutral" | "negative"` — matches `Sentiment` literal in `backend/app/agents/market/schemas.py`
- `RegulationDoc` interface fields match `RegulationDocumentOut` Pydantic model
- `api.chat()` return type `{message: string; thread_id: string}` matches `ChatResponse` from `backend/app/models/chat.py`
- `AllocationChart` receives `weights: {ticker: string; weight: number}[]` — matches component props
- `WorkspaceSwitcher` receives `{current: string | null; onChange: (id: string) => void}` — matches actual component

**Known constraints:**
- News page requires `NEWS_API_KEY` in backend env; shows empty-state message if absent — no crash
- Legal upload skips Pinecone dense re-indexing (BM25 only) — newly uploaded docs are searchable via sparse retrieval only
- `BM25Retriever._chunks` is a private attribute; acceptable since it's internal code
