# Trading Dashboard & Landing Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic dashboard with a professional dark-themed trading terminal (recharts price charts + indicator chips), add a Coinbase-style landing page at `/`, and redesign the sidebar to match.

**Architecture:** A new `GET /api/v1/market/watchlist?tickers=...` backend endpoint fetches 90-day price series with precomputed indicators (SMA20, EMA50, RSI14) from yfinance. The frontend fetches this on mount and renders recharts `ComposedChart` (area + overlays) plus an RSI subplot. The dashboard keeps the existing AI-agent command form below the market section in a white card. The sidebar and landing page adopt the DESIGN.md Coinbase token palette inline via Tailwind arbitrary values.

**Tech Stack:** Next.js 16 App Router, FastAPI, recharts 2.x (`--legacy-peer-deps` for React 19), Tailwind CSS v4 (arbitrary color values), lucide-react, Shadcn UI (existing), yfinance + TA-Lib (existing backend)

## Global Constraints

- Tailwind v4 — use arbitrary values like `bg-[#0a0b0d]` for design token colors; no new CSS variables needed
- Coinbase palette (from DESIGN.md): primary `#0052ff`, surface-dark `#0a0b0d`, surface-dark-elevated `#16181c`, canvas `#ffffff`, semantic-up `#05b169`, semantic-down `#cf202f`, on-dark `#ffffff`, on-dark-soft `#a8acb3`, hairline `#dee1e6`
- `recharts` installed with `npm install recharts --legacy-peer-deps` in `frontend/` — React 19 peer-dep workaround
- All prices displayed in IDR format: `toLocaleString("id-ID")` prefixed with `Rp `
- Default watchlist: `["BBCA.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"]`
- Backend: no auth required on the new `/market/watchlist` endpoint (public market data)
- TypeScript strict — no `any`, no unused imports
- Frequent commits, DRY, YAGNI

---

## File Map

**New:**
- `backend/app/api/v1/market.py` — FastAPI router, `GET /market/watchlist`
- `backend/tests/test_market_endpoint.py` — endpoint test
- `frontend/components/price-chart.tsx` — recharts ComposedChart + RSI subplot
- `frontend/components/ticker-card.tsx` — compact ticker chip (price + change % + RSI badge)

**Modified:**
- `backend/app/agents/market/yfinance_client.py` — add `fetch_price_series_with_indicators()`
- `backend/app/api/v1/router.py` — register market router
- `frontend/lib/api-client.ts` — add `PricePoint`, `TickerChartData`, `api.getWatchlist()`
- `frontend/components/app-sidebar.tsx` — dark theme redesign
- `frontend/app/(protected)/dashboard/page.tsx` — full trading terminal redesign
- `frontend/app/page.tsx` — Coinbase-style landing page

---

## Task 1: Backend — Price Series Function + Market Endpoint

**Files:**
- Modify: `backend/app/agents/market/yfinance_client.py`
- Create: `backend/app/api/v1/market.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/tests/test_market_endpoint.py`

**Interfaces:**
- Produces: `GET /api/v1/market/watchlist?tickers=BBCA.JK,TLKM.JK` → `list[TickerChartData]`
- `TickerChartData` fields: `ticker`, `last_close`, `prev_close`, `price_change_pct`, `rsi14`, `sma20`, `macd`, `bb_upper`, `bb_lower`, `price_series: list[PricePoint]`
- `PricePoint` fields: `date` (str "YYYY-MM-DD"), `close`, `sma20`, `ema50`, `rsi14`

- [ ] **Step 1: Write the failing endpoint test**

Create `backend/tests/test_market_endpoint.py`:

```python
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


FAKE_SERIES = [{"date": "2025-01-01", "close": 9500.0, "sma20": 9400.0, "ema50": 9350.0, "rsi14": 55.0}]

FAKE_TICKER_DATA = {
    "series": FAKE_SERIES,
    "last_close": 9500.0,
    "prev_close": 9400.0,
    "rsi14": 55.0,
    "sma20": 9400.0,
    "macd": 12.0,
    "bb_upper": 10000.0,
    "bb_lower": 9000.0,
}


def test_watchlist_returns_list(client: TestClient) -> None:
    with patch(
        "app.api.v1.market.fetch_price_series_with_indicators",
        return_value=FAKE_TICKER_DATA,
    ):
        response = client.get("/api/v1/market/watchlist?tickers=BBCA.JK")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    item = data[0]
    assert item["ticker"] == "BBCA.JK"
    assert item["last_close"] == 9500.0
    assert item["price_change_pct"] == pytest.approx(1.0638, abs=0.01)
    assert len(item["price_series"]) == 1
    assert item["price_series"][0]["date"] == "2025-01-01"


def test_watchlist_default_tickers(client: TestClient) -> None:
    with patch(
        "app.api.v1.market.fetch_price_series_with_indicators",
        return_value=FAKE_TICKER_DATA,
    ):
        response = client.get("/api/v1/market/watchlist")
    assert response.status_code == 200
    assert len(response.json()) == 4  # default: BBCA.JK, TLKM.JK, ASII.JK, BBRI.JK
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink/backend"
python -m pytest tests/test_market_endpoint.py -v
```
Expected: FAIL — `ModuleNotFoundError` or `404` because route doesn't exist yet.

- [ ] **Step 3: Add `fetch_price_series_with_indicators` to yfinance_client.py**

Open `backend/app/agents/market/yfinance_client.py`. Add at the top with existing imports:

```python
import numpy as np
import yfinance as yf
```

Then add after the existing `_cache` dict and `_CacheEntry` class (keep existing `fetch_close_prices` unchanged):

```python
import datetime


def fetch_price_series_with_indicators(ticker: str, window: int = 90) -> dict:
    """Return `window` trading days of OHLCV + precomputed indicators.

    Fetches 1 year so SMA20/EMA50 are properly warmed before the returned window.
    Returns a dict with keys: series, last_close, prev_close, rsi14, sma20, macd,
    bb_upper, bb_lower.  Any uncomputable value is None.
    """
    from app.agents.market.indicators import compute_indicators  # lazy: avoids TA-Lib at import time

    try:
        df = yf.Ticker(ticker).history(period="1y", auto_adjust=True)
    except Exception as exc:
        log.error("yfinance price_series: failed for %s: %s", ticker, exc)
        return {"series": [], "last_close": None, "prev_close": None,
                "rsi14": None, "sma20": None, "macd": None, "bb_upper": None, "bb_lower": None}

    if df.empty or len(df) < 2:
        return {"series": [], "last_close": None, "prev_close": None,
                "rsi14": None, "sma20": None, "macd": None, "bb_upper": None, "bb_lower": None}

    closes = df["Close"].to_numpy().astype(np.float64)
    dates = [str(idx.date()) for idx in df.index]

    try:
        ind = compute_indicators(closes)
    except Exception as exc:
        log.error("yfinance price_series: indicators failed for %s: %s", ticker, exc)
        ind = {}

    def _float_or_none(arr: "np.ndarray | None", i: int) -> "float | None":
        if arr is None or len(arr) == 0:
            return None
        v = float(arr[i])
        return None if (v != v) else v  # NaN check

    start = max(0, len(closes) - window)
    series = [
        {
            "date": dates[i],
            "close": float(closes[i]),
            "sma20": _float_or_none(ind.get("sma20"), i),
            "ema50": _float_or_none(ind.get("ema50"), i),
            "rsi14": _float_or_none(ind.get("rsi14"), i),
        }
        for i in range(start, len(closes))
    ]

    def _last(key: str) -> "float | None":
        return _float_or_none(ind.get(key), -1) if ind else None

    return {
        "series": series,
        "last_close": float(closes[-1]),
        "prev_close": float(closes[-2]),
        "rsi14": _last("rsi14"),
        "sma20": _last("sma20"),
        "macd": _last("macd"),
        "bb_upper": _last("bb_upper"),
        "bb_lower": _last("bb_lower"),
    }
```

- [ ] **Step 4: Create `backend/app/api/v1/market.py`**

```python
"""Market watchlist endpoint — returns price series + indicators for a set of tickers."""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.agents.market.yfinance_client import fetch_price_series_with_indicators

router = APIRouter()

DEFAULT_TICKERS = "BBCA.JK,TLKM.JK,ASII.JK,BBRI.JK"


class PricePoint(BaseModel):
    date: str
    close: float
    sma20: float | None = None
    ema50: float | None = None
    rsi14: float | None = None


class TickerChartData(BaseModel):
    ticker: str
    last_close: float | None = None
    prev_close: float | None = None
    price_change_pct: float | None = None
    rsi14: float | None = None
    sma20: float | None = None
    macd: float | None = None
    bb_upper: float | None = None
    bb_lower: float | None = None
    price_series: list[PricePoint] = []


@router.get("/watchlist", response_model=list[TickerChartData])
async def get_watchlist(
    tickers: str = Query(default=DEFAULT_TICKERS, description="Comma-separated ticker symbols"),
) -> list[TickerChartData]:
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    result: list[TickerChartData] = []

    for ticker in ticker_list:
        data = fetch_price_series_with_indicators(ticker)

        last_close = data["last_close"]
        prev_close = data["prev_close"]
        change_pct: float | None = None
        if last_close is not None and prev_close is not None and prev_close != 0:
            change_pct = (last_close - prev_close) / prev_close * 100

        result.append(
            TickerChartData(
                ticker=ticker,
                last_close=last_close,
                prev_close=prev_close,
                price_change_pct=change_pct,
                rsi14=data["rsi14"],
                sma20=data["sma20"],
                macd=data["macd"],
                bb_upper=data["bb_upper"],
                bb_lower=data["bb_lower"],
                price_series=[PricePoint(**p) for p in data["series"]],
            )
        )

    return result
```

- [ ] **Step 5: Register market router in `backend/app/api/v1/router.py`**

Current file content:
```python
from fastapi import APIRouter

from app.api.v1 import agent, chat, health, legal
from app.api.v1 import approvals as approvals_router
from app.api.v1 import pin as pin_router
from app.api.v1 import whatsapp as wa_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(legal.router, prefix="/legal", tags=["legal"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(pin_router.router, prefix="/users", tags=["pin"])
api_router.include_router(approvals_router.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(wa_router.router, prefix="/whatsapp", tags=["whatsapp"])
```

Replace with:
```python
from fastapi import APIRouter

from app.api.v1 import agent, chat, health, legal, market
from app.api.v1 import approvals as approvals_router
from app.api.v1 import pin as pin_router
from app.api.v1 import whatsapp as wa_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(legal.router, prefix="/legal", tags=["legal"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(pin_router.router, prefix="/users", tags=["pin"])
api_router.include_router(approvals_router.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(wa_router.router, prefix="/whatsapp", tags=["whatsapp"])
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink/backend"
python -m pytest tests/test_market_endpoint.py -v
```
Expected:
```
PASSED tests/test_market_endpoint.py::test_watchlist_returns_list
PASSED tests/test_market_endpoint.py::test_watchlist_default_tickers
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/market/yfinance_client.py backend/app/api/v1/market.py backend/app/api/v1/router.py backend/tests/test_market_endpoint.py
git commit -m "feat(market): add watchlist endpoint with 90-day price series + indicators"
```

---

## Task 2: Frontend — Install recharts + Extend API Client

**Files:**
- Modify: `frontend/lib/api-client.ts`

**Interfaces:**
- Consumes: nothing from prior tasks (backend not called until Task 5 wires it into the page)
- Produces:
  - `PricePoint` type exported from `api-client.ts`
  - `TickerChartData` type exported from `api-client.ts`
  - `api.getWatchlist(tickers: string[]): Promise<TickerChartData[]>`

- [ ] **Step 1: Install recharts**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink/frontend"
npm install recharts --legacy-peer-deps
```
Expected: `recharts` appears in `frontend/node_modules/recharts/` with no fatal errors (peer dep warnings about React 19 are ok).

- [ ] **Step 2: Verify TypeScript resolves recharts types**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink/frontend"
npx tsc --noEmit 2>&1 | head -20
```
Expected: Either 0 errors, or the same errors that existed before (from other files) — no new errors from recharts.

- [ ] **Step 3: Add types + getWatchlist to `frontend/lib/api-client.ts`**

Read the file first, then append these additions **before the closing brace of `api`** (or at module scope if api is a namespace):

Add new types at module scope (after existing `AgentRunResponse`):

```ts
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
```

Add `getWatchlist` to the `api` object:

```ts
async getWatchlist(tickers: string[]): Promise<TickerChartData[]> {
  const params = new URLSearchParams({ tickers: tickers.join(",") });
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/market/watchlist?${params}`);
  if (!res.ok) throw new Error(`market/watchlist: ${res.status}`);
  return res.json() as Promise<TickerChartData[]>;
},
```

- [ ] **Step 4: Verify TypeScript**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink/frontend"
npx tsc --noEmit 2>&1 | grep -v "node_modules" | head -20
```
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/lib/api-client.ts
git commit -m "feat(frontend): install recharts + add market watchlist api types"
```

---

## Task 3: Frontend — PriceChart Component

**Files:**
- Create: `frontend/components/price-chart.tsx`

**Interfaces:**
- Consumes: `PricePoint` from `@/lib/api-client`
- Produces: `<PriceChart ticker data lastClose priceChangePct bbUpper bbLower />`

- [ ] **Step 1: Create `frontend/components/price-chart.tsx`**

```tsx
"use client";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PricePoint } from "@/lib/api-client";

interface PriceChartProps {
  ticker: string;
  data: PricePoint[];
  lastClose: number | null;
  priceChangePct: number | null;
  bbUpper: number | null;
  bbLower: number | null;
}

const TOOLTIP_STYLE = {
  background: "#16181c",
  border: "1px solid #2a2d36",
  color: "#ffffff",
  borderRadius: "8px",
  fontSize: "12px",
};

function formatIDR(v: number): string {
  return `Rp ${v.toLocaleString("id-ID")}`;
}

export function PriceChart({
  ticker,
  data,
  lastClose,
  priceChangePct,
  bbUpper,
  bbLower,
}: PriceChartProps) {
  const isUp = (priceChangePct ?? 0) >= 0;
  const changeColor = isUp ? "#05b169" : "#cf202f";

  const priceData = data.map((d) => ({
    date: d.date.slice(5), // "MM-DD"
    close: d.close,
    sma20: d.sma20,
    ema50: d.ema50,
  }));

  const rsiData = data.map((d) => ({
    date: d.date.slice(5),
    rsi14: d.rsi14,
  }));

  return (
    <div>
      {/* Price header */}
      <div className="flex items-baseline gap-3 mb-3">
        <span className="font-mono text-2xl font-medium text-white">
          {lastClose != null ? formatIDR(lastClose) : "—"}
        </span>
        <span className="font-mono text-sm" style={{ color: changeColor }}>
          {priceChangePct != null
            ? `${priceChangePct >= 0 ? "+" : ""}${priceChangePct.toFixed(2)}%`
            : ""}
        </span>
        {bbUpper != null && bbLower != null && (
          <span className="text-[#a8acb3] text-xs font-mono">
            BB {formatIDR(bbLower)}–{formatIDR(bbUpper)}
          </span>
        )}
      </div>

      {/* Main price chart */}
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={priceData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0052ff" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#0052ff" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2028" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#a8acb3", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#a8acb3", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => v.toLocaleString("id-ID")}
            width={76}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(v: number, name: string) => [
              formatIDR(v),
              name === "close" ? "Harga" : name === "sma20" ? "SMA20" : "EMA50",
            ]}
          />
          <Area
            type="monotone"
            dataKey="close"
            stroke="#0052ff"
            strokeWidth={2}
            fill="url(#priceGrad)"
            dot={false}
            activeDot={{ r: 4, fill: "#0052ff" }}
          />
          <Line
            type="monotone"
            dataKey="sma20"
            stroke="#f4b000"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 2"
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="ema50"
            stroke="#a8acb3"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 2"
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* RSI subplot label */}
      <div className="text-[#a8acb3] text-[10px] font-mono mt-2 mb-1">RSI 14</div>

      {/* RSI chart */}
      <ResponsiveContainer width="100%" height={72}>
        <LineChart data={rsiData} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2028" vertical={false} />
          <XAxis dataKey="date" hide />
          <YAxis
            domain={[0, 100]}
            ticks={[30, 50, 70]}
            tick={{ fill: "#a8acb3", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={76}
          />
          <ReferenceLine y={70} stroke="#cf202f" strokeDasharray="3 3" strokeWidth={1} />
          <ReferenceLine y={30} stroke="#05b169" strokeDasharray="3 3" strokeWidth={1} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(v: number) => [v.toFixed(1), "RSI14"]}
          />
          <Line
            type="monotone"
            dataKey="rsi14"
            stroke="#a8acb3"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex gap-4 mt-2 text-[10px] font-mono text-[#a8acb3]">
        <span><span className="inline-block w-3 h-0.5 bg-[#0052ff] mr-1 align-middle" />Harga</span>
        <span><span className="inline-block w-3 h-0.5 bg-[#f4b000] mr-1 align-middle" style={{ borderTop: "1.5px dashed #f4b000" }} />SMA20</span>
        <span><span className="inline-block w-3 h-0.5 bg-[#a8acb3] mr-1 align-middle" style={{ borderTop: "1.5px dashed #a8acb3" }} />EMA50</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink/frontend"
npx tsc --noEmit 2>&1 | grep "price-chart" | head -10
```
Expected: no lines output (no errors in price-chart.tsx).

- [ ] **Step 3: Commit**

```bash
git add frontend/components/price-chart.tsx
git commit -m "feat(frontend): add PriceChart component with recharts ComposedChart + RSI subplot"
```

---

## Task 4: Frontend — TickerCard Component + Dark Sidebar

**Files:**
- Create: `frontend/components/ticker-card.tsx`
- Modify: `frontend/components/app-sidebar.tsx`

**Interfaces:**
- Consumes: nothing from prior tasks at runtime
- Produces:
  - `<TickerCard ticker lastClose priceChangePct rsi14 selected onClick />`
  - `<AppSidebar />` (same interface, dark theme)

- [ ] **Step 1: Create `frontend/components/ticker-card.tsx`**

```tsx
interface TickerCardProps {
  ticker: string;
  lastClose: number | null;
  priceChangePct: number | null;
  rsi14: number | null;
  selected?: boolean;
  onClick: () => void;
}

export function TickerCard({
  ticker,
  lastClose,
  priceChangePct,
  rsi14,
  selected = false,
  onClick,
}: TickerCardProps) {
  const symbol = ticker.replace(".JK", "");
  const isUp = (priceChangePct ?? 0) >= 0;
  const rsiLabel =
    rsi14 != null ? (rsi14 > 70 ? "OB" : rsi14 < 30 ? "OS" : null) : null;

  return (
    <button
      onClick={onClick}
      type="button"
      className={`rounded-xl p-4 text-left w-full transition-all border ${
        selected
          ? "border-[#0052ff] bg-[#0a1a3a]"
          : "border-[#2a2d36] bg-[#16181c] hover:border-[#0052ff]/50 hover:bg-[#1a1c22]"
      }`}
    >
      <div className="font-mono font-semibold text-white text-sm">{symbol}</div>
      <div className="mt-1 font-mono text-base text-white leading-none">
        {lastClose != null
          ? `Rp ${lastClose.toLocaleString("id-ID")}`
          : <span className="text-[#a8acb3]">—</span>}
      </div>
      <div
        className="font-mono text-xs mt-1"
        style={{ color: isUp ? "#05b169" : "#cf202f" }}
      >
        {priceChangePct != null
          ? `${isUp ? "+" : ""}${priceChangePct.toFixed(2)}%`
          : "—"}
      </div>
      {rsiLabel && (
        <span className="mt-1.5 inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-[#2a2d36] text-[#a8acb3]">
          {rsiLabel}
        </span>
      )}
    </button>
  );
}
```

- [ ] **Step 2: Rewrite `frontend/components/app-sidebar.tsx`**

Read the current file first, then replace entire contents with:

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ArrowLeftRight,
  CheckSquare,
  LayoutDashboard,
  Settings,
} from "lucide-react";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/transactions", label: "Transaksi", icon: ArrowLeftRight },
  { href: "/settings", label: "Pengaturan", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 bg-[#0a0b0d] min-h-screen border-r border-[#1e2028] flex flex-col">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-[#1e2028]">
        <span className="text-white font-semibold text-base tracking-tight">
          Astalink
        </span>
        <span className="ml-1.5 text-[#0052ff] text-xs font-mono font-bold">
          AI
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-[#16181c] text-white border-l-2 border-[#0052ff] pl-[10px]"
                  : "text-[#a8acb3] hover:bg-[#16181c] hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink/frontend"
npx tsc --noEmit 2>&1 | grep -E "(ticker-card|app-sidebar)" | head -10
```
Expected: no lines (no errors in these files).

- [ ] **Step 4: Commit**

```bash
git add frontend/components/ticker-card.tsx frontend/components/app-sidebar.tsx
git commit -m "feat(frontend): add TickerCard component + dark sidebar redesign"
```

---

## Task 5: Frontend — Dashboard Page Redesign

**Files:**
- Modify: `frontend/app/(protected)/dashboard/page.tsx`

**Interfaces:**
- Consumes:
  - `PriceChart` from `@/components/price-chart` (Task 3)
  - `TickerCard` from `@/components/ticker-card` (Task 4)
  - `api.getWatchlist(tickers: string[]): Promise<TickerChartData[]>` (Task 2)
  - `TickerChartData` type from `@/lib/api-client` (Task 2)
  - Existing: `WorkspaceSwitcher`, `AllocationChart`, `api.runAgent`, `AgentRunResponse`, Supabase client, `toast`

- [ ] **Step 1: Read current dashboard page**

Read `frontend/app/(protected)/dashboard/page.tsx` in full (152 lines). Note the existing state variables, handler functions, and imports — the new version preserves the agent run logic entirely.

- [ ] **Step 2: Replace dashboard page**

Write the entire file:

```tsx
"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { AllocationChart } from "@/components/allocation-chart";
import { PriceChart } from "@/components/price-chart";
import { TickerCard } from "@/components/ticker-card";
import { createClient } from "@/lib/supabase/client";
import { api, type AgentRunResponse, type TickerChartData } from "@/lib/api-client";

const DEFAULT_WATCHLIST = ["BBCA.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"];

const legalColor: Record<string, string> = {
  approved: "bg-green-100 text-green-800",
  partial: "bg-yellow-100 text-yellow-800",
  rejected: "bg-red-100 text-red-800",
  rejected_after_max_revisions: "bg-red-100 text-red-800",
};

export default function DashboardPage() {
  const router = useRouter();

  // Market state
  const [watchlist, setWatchlist] = useState<TickerChartData[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>(DEFAULT_WATCHLIST[0]);
  const [marketLoading, setMarketLoading] = useState(true);

  // Agent state
  const [workspaceId, setWorkspaceId] = useState<string>("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentRunResponse | null>(null);

  // Fetch watchlist on mount
  useEffect(() => {
    api
      .getWatchlist(DEFAULT_WATCHLIST)
      .then((data) => setWatchlist(data))
      .catch(() => {}) // network or backend unavailable — silent; skeleton shows
      .finally(() => setMarketLoading(false));
  }, []);

  const selectedData = watchlist.find((t) => t.ticker === selectedTicker) ?? null;

  async function handleRun() {
    const sb = createClient();
    const { data: { user } } = await sb.auth.getUser();
    if (!user) { router.push("/login"); return; }

    setLoading(true);
    setResult(null);
    try {
      const res = await api.runAgent({ message, workspace_id: workspaceId });
      setResult(res);
      const ls = res.legal_status ?? "";
      if (!["rejected", "rejected_after_max_revisions"].includes(ls)) {
        toast.success("Analisis selesai — silakan tinjau alokasi di bawah.");
      } else {
        toast.error(`Ditolak secara legal: ${ls}`);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal menghubungi agen.");
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    if (!result) return;
    router.push(`/approvals/${result.audit_id}`);
  }

  const isRejected = ["rejected", "rejected_after_max_revisions"].includes(
    result?.legal_status ?? ""
  );

  return (
    <div className="min-h-screen bg-[#0a0b0d] flex flex-col">
      {/* ── Market Watch Header ── */}
      <div className="border-b border-[#1e2028] px-6 py-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-[#a8acb3] text-[10px] font-mono uppercase tracking-widest">
              Market Watch
            </p>
            <h1 className="text-white text-lg font-semibold leading-tight mt-0.5">
              IDX Blue Chips
            </h1>
          </div>
          <WorkspaceSwitcher onWorkspaceChange={setWorkspaceId} />
        </div>

        {/* Ticker grid */}
        <div className="grid grid-cols-4 gap-3">
          {DEFAULT_WATCHLIST.map((ticker) => {
            const data = watchlist.find((t) => t.ticker === ticker);
            return (
              <TickerCard
                key={ticker}
                ticker={ticker}
                lastClose={marketLoading ? null : (data?.last_close ?? null)}
                priceChangePct={marketLoading ? null : (data?.price_change_pct ?? null)}
                rsi14={marketLoading ? null : (data?.rsi14 ?? null)}
                selected={selectedTicker === ticker}
                onClick={() => setSelectedTicker(ticker)}
              />
            );
          })}
        </div>
      </div>

      {/* ── Chart Area ── */}
      <div className="px-6 py-5 border-b border-[#1e2028]">
        {marketLoading ? (
          <div className="h-64 flex items-center justify-center text-[#a8acb3] text-sm font-mono">
            Memuat data pasar…
          </div>
        ) : selectedData && selectedData.price_series.length > 0 ? (
          <PriceChart
            ticker={selectedData.ticker}
            data={selectedData.price_series}
            lastClose={selectedData.last_close}
            priceChangePct={selectedData.price_change_pct}
            bbUpper={selectedData.bb_upper}
            bbLower={selectedData.bb_lower}
          />
        ) : (
          <div className="h-64 flex items-center justify-center text-[#a8acb3] text-sm font-mono">
            Data tidak tersedia untuk {selectedTicker}
          </div>
        )}
      </div>

      {/* ── AI Agent Section ── */}
      <div className="px-6 py-6 flex-1">
        <div className="bg-white rounded-2xl p-6">
          <h2 className="text-[#0a0b0d] font-semibold text-base mb-1">Perintah AI</h2>
          <p className="text-[#5b616e] text-sm mb-4">
            Deskripsikan tujuan investasi Anda. AI akan menganalisis pasar, bisnis, risiko, dan legalitas.
          </p>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Contoh: Analisis dan optimalkan portofolio saya dengan fokus BBCA dan TLKM, toleransi risiko sedang."
            className="w-full rounded-xl border border-[#dee1e6] px-4 py-3 text-[#0a0b0d] text-sm resize-none focus:outline-none focus:border-[#0052ff] focus:ring-1 focus:ring-[#0052ff] transition-colors"
            rows={3}
          />
          <div className="flex justify-end mt-3">
            <button
              onClick={handleRun}
              disabled={loading || !message.trim()}
              className="px-6 py-2.5 rounded-full bg-[#0052ff] text-white text-sm font-semibold hover:bg-[#003ecc] disabled:bg-[#a8b8cc] disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Menganalisis…" : "Jalankan"}
            </button>
          </div>
        </div>

        {/* ── Agent Result ── */}
        {result && (
          <div className="mt-4 bg-white rounded-2xl p-6 space-y-4">
            {/* Header row */}
            <div className="flex items-center gap-3 flex-wrap">
              {result.intent && (
                <Badge variant="outline" className="font-mono text-xs">
                  {result.intent}
                </Badge>
              )}
              {result.legal_status && (
                <span
                  className={`rounded-full px-3 py-0.5 text-xs font-semibold ${
                    legalColor[result.legal_status] ?? "bg-gray-100 text-gray-800"
                  }`}
                >
                  {result.legal_status}
                </span>
              )}
            </div>

            {/* Allocation chart */}
            {result.allocation_plan && (
              <>
                <Separator />
                <div>
                  <p className="text-xs font-medium text-[#5b616e] mb-3">Alokasi Portofolio</p>
                  <AllocationChart weights={result.allocation_plan.weights} />
                  {result.allocation_plan.narration && (
                    <p className="text-sm text-[#5b616e] mt-3 leading-relaxed">
                      {result.allocation_plan.narration}
                    </p>
                  )}
                </div>
              </>
            )}

            {/* Errors */}
            {result.errors.length > 0 && (
              <>
                <Separator />
                <div className="space-y-1">
                  {result.errors.map((e, i) => (
                    <p key={i} className="text-xs text-red-600 font-mono">
                      [{e.node}] {e.reason}
                    </p>
                  ))}
                </div>
              </>
            )}

            {/* Approve button */}
            {!isRejected && result.user_approval === "pending" && (
              <>
                <Separator />
                <div className="flex justify-end">
                  <button
                    onClick={handleApprove}
                    className="px-6 py-2.5 rounded-full bg-[#0052ff] text-white text-sm font-semibold hover:bg-[#003ecc] transition-colors"
                  >
                    Tinjau & Setujui
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

> **Note:** `WorkspaceSwitcher` receives an `onWorkspaceChange` prop so the dashboard captures the selected workspace ID. If the current `WorkspaceSwitcher` component doesn't accept this prop, read its file and add: `onWorkspaceChange?: (id: string) => void` to its props interface, then call it inside the selection handler. Do NOT change the visual behavior of `WorkspaceSwitcher`.

- [ ] **Step 3: Verify TypeScript**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink/frontend"
npx tsc --noEmit 2>&1 | grep "dashboard" | head -10
```
Expected: no errors in the dashboard file.

- [ ] **Step 4: Lint check**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink/frontend"
npm run lint 2>&1 | tail -5
```
Expected: no errors (warnings are ok).

- [ ] **Step 5: Commit**

```bash
git add "frontend/app/(protected)/dashboard/page.tsx" frontend/components/workspace-switcher.tsx
git commit -m "feat(frontend): trading terminal dashboard with recharts price chart + indicator chips"
```

---

## Task 6: Frontend — Landing Page

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: nothing from prior tasks
- Produces: Coinbase-style marketing page at `/` with dark hero, feature grid, CTA band

- [ ] **Step 1: Replace `frontend/app/page.tsx`**

```tsx
import Link from "next/link";
import { Shield, TrendingUp, UserCheck } from "lucide-react";

const FEATURES = [
  {
    icon: TrendingUp,
    title: "Analisis Multi-Dimensi",
    desc: "AI menganalisis data pasar real-time, fundamental bisnis, dan risiko portofolio secara bersamaan untuk rekomendasi alokasi yang optimal.",
  },
  {
    icon: Shield,
    title: "Kepatuhan Hukum Otomatis",
    desc: "Setiap alokasi diverifikasi terhadap regulasi IDX dan OJK secara otomatis sebelum diteruskan — tidak ada celah kepatuhan.",
  },
  {
    icon: UserCheck,
    title: "Kontrol di Tangan Anda",
    desc: "Tidak ada transaksi tanpa PIN konfirmasi Anda. Human-in-the-loop bawaan memastikan Anda selalu yang memutuskan terakhir.",
  },
] as const;

export default function Home() {
  return (
    <div className="min-h-screen">
      {/* ── Dark Hero ── */}
      <section className="bg-[#0a0b0d] px-6 py-28 text-center">
        <div className="mx-auto max-w-2xl">
          <p className="text-[#0052ff] text-[11px] font-semibold uppercase tracking-[0.2em] mb-5">
            Astalink AI
          </p>
          <h1 className="text-white text-5xl font-normal leading-[1.05] tracking-tight mb-6">
            Investasi Saham IDX
            <br />
            dengan Kecerdasan AI
          </h1>
          <p className="text-[#a8acb3] text-lg leading-relaxed mb-10 max-w-lg mx-auto">
            Analisis pasar otomatis, kepatuhan hukum bawaan, dan persetujuan
            pengguna sebelum setiap transaksi.
          </p>
          <div className="flex gap-3 justify-center">
            <Link
              href="/signup"
              className="px-8 py-3 rounded-full bg-[#0052ff] text-white font-semibold text-sm hover:bg-[#003ecc] transition-colors"
            >
              Mulai Sekarang
            </Link>
            <Link
              href="/login"
              className="px-8 py-3 rounded-full border border-white/20 text-white font-semibold text-sm hover:border-white/50 transition-colors"
            >
              Login
            </Link>
          </div>
        </div>
      </section>

      {/* ── Feature Grid ── */}
      <section className="bg-white px-6 py-24">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-[#0a0b0d] text-3xl font-normal text-center tracking-tight mb-12">
            Cara Kerja Astalink
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="rounded-2xl border border-[#dee1e6] p-8"
              >
                <div className="w-10 h-10 rounded-full bg-[#eef0f3] flex items-center justify-center mb-5">
                  <Icon className="h-5 w-5 text-[#0052ff]" />
                </div>
                <h3 className="text-[#0a0b0d] font-semibold text-base mb-2">
                  {title}
                </h3>
                <p className="text-[#5b616e] text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats Band (light gray) ── */}
      <section className="bg-[#f7f7f7] px-6 py-16">
        <div className="mx-auto max-w-3xl grid grid-cols-3 gap-8 text-center">
          {[
            { value: "5", label: "Node AI Pipeline" },
            { value: "4", label: "Indikator Teknikal" },
            { value: "100%", label: "Kontrol Pengguna" },
          ].map(({ value, label }) => (
            <div key={label}>
              <div className="font-mono text-4xl font-medium text-[#0a0b0d]">
                {value}
              </div>
              <div className="text-[#5b616e] text-sm mt-1">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Dark CTA Band ── */}
      <section className="bg-[#0a0b0d] px-6 py-24 text-center">
        <h2 className="text-white text-4xl font-normal tracking-tight mb-6">
          Siap investasi lebih cerdas?
        </h2>
        <p className="text-[#a8acb3] text-base mb-8">
          Buat akun gratis dan mulai analisis portofolio pertama Anda dalam menit.
        </p>
        <Link
          href="/signup"
          className="inline-block px-10 py-4 rounded-full bg-[#0052ff] text-white font-semibold text-base hover:bg-[#003ecc] transition-colors"
        >
          Buat Akun Gratis
        </Link>
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript + lint**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink/frontend"
npx tsc --noEmit 2>&1 | grep "page.tsx" | grep -v "protected" | head -10
npm run lint 2>&1 | tail -5
```
Expected: no errors.

- [ ] **Step 3: Verify the app builds**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink/frontend"
npm run build 2>&1 | tail -20
```
Expected: `✓ Compiled successfully` (or equivalent Next.js 16 success output). If there are errors, fix them before committing.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat(frontend): Coinbase-style landing page with dark hero + feature grid + CTA band"
```

---

## Self-Review

**Spec coverage:**
- ✅ Professional trading charts: Task 3 (`PriceChart`) — recharts ComposedChart with price area, SMA20, EMA50, RSI subplot
- ✅ Backend market data: Task 1 — new `/api/v1/market/watchlist` returning 90-day price series
- ✅ Ticker watchlist with price change %: Task 4 (`TickerCard`) + Task 5 (dashboard grid)
- ✅ Coinbase design tokens: Tasks 4, 5, 6 — `#0052ff`, `#0a0b0d`, `#16181c`, `#05b169`, `#cf202f` inline
- ✅ Dark sidebar: Task 4 (`app-sidebar.tsx`)
- ✅ Landing page at `/`: Task 6
- ✅ Existing agent form preserved: Task 5 (white card section below charts)
- ✅ Tests: Task 1 has two pytest tests

**Placeholder scan:** None found — all steps contain full code.

**Type consistency:**
- `PricePoint` defined in `api-client.ts` (Task 2), imported by `price-chart.tsx` (Task 3) ✅
- `TickerChartData` defined in `api-client.ts` (Task 2), used in `dashboard/page.tsx` (Task 5) ✅
- `TickerCard` props match exactly what Task 5 passes ✅
- `PriceChart` props match exactly what Task 5 passes ✅
- Backend `TickerChartData` model fields match frontend type field names (snake_case both sides) ✅
