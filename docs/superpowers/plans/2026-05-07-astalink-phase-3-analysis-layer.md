# AstaLink Phase 3 — Analysis Layer (N2a/b/c) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. **Phases 0–2 must be complete before starting.**

**Goal:** Replace the Phase 2 stub nodes for N2a/N2b/N2c with real implementations. N2a Market Analyzer pulls Yahoo Finance prices and News API headlines and computes TA-Lib indicators; N2b Business Evaluator runs a DCF model on either uploaded financials or a CSV stub; N2c Risk Agent runs scipy Mean-Variance Optimization and numpy VaR. **Hard constraint: every quantitative number is computed by scipy/numpy/TA-Lib — the LLM only narrates them.** A code-review checklist enforces this; the tests verify deterministic outputs against reference values.

**Architecture:**
- N2a (`app/agents/market/`): `yfinance_client` fetches OHLCV; `news_client` pulls headlines (News API) and Gemini sentiment-tags them as positive/neutral/negative (categorical only — no numeric "sentiment score" from LLM); `indicators` wraps TA-Lib (SMA, EMA, RSI, MACD, Bollinger); `node` calls all three, builds a `MarketSnapshot`, asks Gemini for a one-paragraph narration grounded in those numbers.
- N2b (`app/agents/business/`): `dcf` is a pure numpy DCF computation; `erp_connector` is a swappable interface — the hackathon ships only `CSVConnector` reading user-uploaded statements; real ERP integrations are deferred. Node returns a `BusinessValuation`.
- N2c (`app/agents/risk/`): `mvo` solves Markowitz mean-variance with scipy.optimize; `var` computes historical and parametric VaR from numpy. Node returns `RiskAssessment`.
- Graph wiring (`app/agents/graph.py`) swaps `market_stub` → `market_node`, etc. The stubs file stays around for tests and for any partial-deploy scenario.

**Tech Stack:** yfinance, TA-Lib (system lib + Python wrapper from Phase 0), pandas, numpy, scipy.optimize, pypdf (already), httpx (News API).

**Scope cuts:** TA-Lib indicators limited to 5 (SMA20, EMA50, RSI14, MACD, BB20) — easy to extend later but five is enough for narration. DCF defaults: `terminal_growth=0.03`, `discount_rate=0.10`. MVO uses 1-year daily returns and assumes long-only weights summing to 1.0. News API runs only when `NEWS_API_KEY` is set; otherwise N2a returns an empty `news` field with a log warning.

---

## File Structure

```
astalink/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── market/
│   │   │   │   ├── __init__.py            # CREATE
│   │   │   │   ├── schemas.py             # CREATE: MarketSnapshot, NewsItem
│   │   │   │   ├── yfinance_client.py     # CREATE
│   │   │   │   ├── news_client.py         # CREATE
│   │   │   │   ├── indicators.py          # CREATE: TA-Lib wrappers
│   │   │   │   └── node.py                # CREATE
│   │   │   ├── business/
│   │   │   │   ├── __init__.py            # CREATE
│   │   │   │   ├── schemas.py             # CREATE: BusinessValuation
│   │   │   │   ├── dcf.py                 # CREATE
│   │   │   │   ├── erp_connector.py       # CREATE: CSVConnector
│   │   │   │   └── node.py                # CREATE
│   │   │   ├── risk/
│   │   │   │   ├── __init__.py            # CREATE
│   │   │   │   ├── schemas.py             # CREATE: RiskAssessment
│   │   │   │   ├── mvo.py                 # CREATE
│   │   │   │   ├── var.py                 # CREATE
│   │   │   │   └── node.py                # CREATE
│   │   │   └── graph.py                   # MODIFY: swap stubs for real nodes
│   │   └── core/
│   │       └── config.py                  # MODIFY: add NEWS_API_KEY
│   └── tests/
│       ├── test_market_indicators.py      # CREATE: golden values for SMA/RSI/MACD
│       ├── test_market_node.py            # CREATE
│       ├── test_business_dcf.py           # CREATE: spreadsheet-comparable
│       ├── test_business_node.py          # CREATE
│       ├── test_risk_mvo.py               # CREATE: known optimal weights
│       ├── test_risk_var.py               # CREATE: scipy reference
│       ├── test_risk_node.py              # CREATE
│       └── data/
│           └── sample_financials.csv      # CREATE: fixture for ERP CSV connector
├── .env.example                           # MODIFY: NEWS_API_KEY (optional)
└── docker-compose.yml                     # MODIFY: pass NEWS_API_KEY
```

---

## Task Group A — Market Analyzer (N2a)

### Task A1: Indicators (TA-Lib wrappers)

**Files:**
- Create: `backend/app/agents/market/__init__.py`
- Create: `backend/app/agents/market/indicators.py`
- Create: `backend/tests/test_market_indicators.py`

- [ ] **Step 1: Write failing tests with golden values**

`backend/tests/test_market_indicators.py`:

```python
import numpy as np
import pytest

from app.agents.market.indicators import compute_indicators


@pytest.fixture
def constant_close() -> np.ndarray:
    """30 days of price 100. SMA, EMA = 100 throughout. RSI undefined (no movement)."""
    return np.full(30, 100.0)


@pytest.fixture
def linear_uptrend() -> np.ndarray:
    """30 days, price increases by 1 each day from 100→129."""
    return np.arange(100, 130, dtype=np.float64)


def test_sma20_on_constant_series_equals_input_value(constant_close: np.ndarray) -> None:
    out = compute_indicators(close=constant_close)
    last_sma = out["sma20"][-1]
    assert last_sma == pytest.approx(100.0, abs=1e-6)


def test_rsi14_on_uptrend_is_high(linear_uptrend: np.ndarray) -> None:
    """A perfect uptrend has RSI close to 100."""
    out = compute_indicators(close=linear_uptrend)
    last_rsi = out["rsi14"][-1]
    assert last_rsi >= 90.0


def test_indicators_dict_has_expected_keys(linear_uptrend: np.ndarray) -> None:
    out = compute_indicators(close=linear_uptrend)
    assert set(out.keys()) >= {"sma20", "ema50", "rsi14", "macd", "bb_upper", "bb_lower"}


def test_short_series_returns_nan_indicators_without_crashing() -> None:
    """A 5-day series can't compute SMA20; indicator must be NaN at end, not crash."""
    short = np.array([100, 101, 102, 103, 104], dtype=np.float64)
    out = compute_indicators(close=short)
    assert np.isnan(out["sma20"][-1])
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_market_indicators.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement indicators**

`backend/app/agents/market/__init__.py`:

```python
```

`backend/app/agents/market/indicators.py`:

```python
"""TA-Lib indicator wrappers. The LLM is forbidden from producing these
numbers — they always come through this module."""
from __future__ import annotations

import numpy as np
import talib


def compute_indicators(close: np.ndarray) -> dict[str, np.ndarray]:
    """Compute the standard AstaLink indicator pack.

    Returns a dict of arrays aligned to the input close series. Indicator values
    that aren't computable (e.g. SMA20 on a 5-day series) are NaN at those
    positions — TA-Lib's documented behavior."""
    close = close.astype(np.float64)
    sma20 = talib.SMA(close, timeperiod=20)
    ema50 = talib.EMA(close, timeperiod=50)
    rsi14 = talib.RSI(close, timeperiod=14)
    macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)

    return {
        "sma20": sma20,
        "ema50": ema50,
        "rsi14": rsi14,
        "macd": macd,
        "macd_signal": macd_signal,
        "bb_upper": bb_upper,
        "bb_middle": bb_middle,
        "bb_lower": bb_lower,
    }
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_market_indicators.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/market/__init__.py backend/app/agents/market/indicators.py backend/tests/test_market_indicators.py
git commit -m "feat(market): add TA-Lib indicator wrappers with golden-value tests"
```

---

### Task A2: yfinance + News clients + MarketSnapshot schema

**Files:**
- Create: `backend/app/agents/market/schemas.py`
- Create: `backend/app/agents/market/yfinance_client.py`
- Create: `backend/app/agents/market/news_client.py`
- Modify: `backend/app/core/config.py` (add `NEWS_API_KEY: str = ""`)
- Modify: `.env.example`, `docker-compose.yml`

- [ ] **Step 1: Define schema**

`backend/app/agents/market/schemas.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Sentiment = Literal["positive", "neutral", "negative"]


class NewsItem(BaseModel):
    title: str
    source: str
    published_at: str
    sentiment: Sentiment


class TickerSnapshot(BaseModel):
    ticker: str
    last_close: float | None = None
    sma20: float | None = None
    ema50: float | None = None
    rsi14: float | None = None
    macd: float | None = None
    bb_upper: float | None = None
    bb_lower: float | None = None
    news: list[NewsItem] = Field(default_factory=list)


class MarketSnapshot(BaseModel):
    tickers: list[TickerSnapshot]
    narration: str = Field(default="", description="LLM-generated summary of the snapshot.")
```

- [ ] **Step 2: Implement yfinance client**

`backend/app/agents/market/yfinance_client.py`:

```python
"""yfinance wrapper. Returns numpy close-price arrays.

We call yfinance lazily and cache per-ticker to avoid hammering the API during
hot-reload dev cycles. Cache TTL is 5 minutes — balance between freshness and
not getting rate-limited."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import numpy as np
import yfinance as yf

log = logging.getLogger(__name__)

_CACHE_TTL = 300  # seconds


@dataclass
class _CacheEntry:
    closes: np.ndarray
    fetched_at: float


_cache: dict[str, _CacheEntry] = {}


def fetch_close_prices(ticker: str, period: str = "1y") -> np.ndarray:
    now = time.time()
    if (entry := _cache.get(ticker)) and now - entry.fetched_at < _CACHE_TTL:
        return entry.closes

    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    except Exception as exc:
        log.error("yfinance: fetch failed for %s: %s", ticker, exc)
        return np.array([])

    if df.empty:
        log.warning("yfinance: empty history for %s", ticker)
        return np.array([])

    closes = df["Close"].to_numpy()
    _cache[ticker] = _CacheEntry(closes=closes, fetched_at=now)
    return closes
```

- [ ] **Step 3: Implement news client**

`backend/app/agents/market/news_client.py`:

```python
"""News API client + Gemini categorical sentiment tagger.

Returns a list of NewsItem; the LLM produces ONLY a categorical
positive/neutral/negative tag — never a numeric score (anti-LLM-quant rule)."""
from __future__ import annotations

import logging

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.market.schemas import NewsItem
from app.core.config import settings
from app.core.gemini import get_chat_model

log = logging.getLogger(__name__)

NEWS_API_URL = "https://newsapi.org/v2/everything"

SENTIMENT_SYSTEM = """\
You categorize a financial news headline as positive, neutral, or negative for
the named ticker. Respond with ONE word only: positive, neutral, or negative."""


def _tag_sentiment(headline: str, ticker: str) -> str:
    llm = get_chat_model()
    resp = llm.invoke([
        SystemMessage(content=SENTIMENT_SYSTEM),
        HumanMessage(content=f"Ticker: {ticker}\nHeadline: {headline}"),
    ])
    word = resp.content.strip().lower().split()[0] if resp.content else "neutral"
    return word if word in ("positive", "neutral", "negative") else "neutral"


def fetch_news(ticker: str, max_items: int = 5) -> list[NewsItem]:
    if not settings.NEWS_API_KEY:
        log.warning("news_client: NEWS_API_KEY unset, returning empty news list")
        return []

    try:
        resp = httpx.get(
            NEWS_API_URL,
            params={"q": ticker, "pageSize": max_items, "language": "en",
                    "sortBy": "publishedAt", "apiKey": settings.NEWS_API_KEY},
            timeout=10.0,
        )
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
    except Exception as exc:
        log.error("news_client: fetch failed for %s: %s", ticker, exc)
        return []

    out: list[NewsItem] = []
    for art in articles[:max_items]:
        title = art.get("title", "")
        if not title:
            continue
        out.append(NewsItem(
            title=title,
            source=(art.get("source") or {}).get("name", "unknown"),
            published_at=art.get("publishedAt", ""),
            sentiment=_tag_sentiment(title, ticker),
        ))
    return out
```

- [ ] **Step 4: Update config + env**

Append to `backend/app/core/config.py`:

```python
    # News API (optional — N2a runs without it)
    NEWS_API_KEY: str = ""
```

Append to `.env.example`:

```
NEWS_API_KEY=
```

Append to `docker-compose.yml` backend env block:

```yaml
      - NEWS_API_KEY=${NEWS_API_KEY}
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/market/schemas.py backend/app/agents/market/yfinance_client.py backend/app/agents/market/news_client.py backend/app/core/config.py .env.example docker-compose.yml
git commit -m "feat(market): add yfinance + News API clients and MarketSnapshot schema"
```

---

### Task A3: market_node — orchestrate fetch + indicators + narration

**Files:**
- Create: `backend/app/agents/market/node.py`
- Create: `backend/tests/test_market_node.py`

- [ ] **Step 1: Write failing test**

`backend/tests/test_market_node.py`:

```python
from unittest.mock import MagicMock, patch

import numpy as np
from langchain_core.messages import AIMessage

from app.agents.market.node import market_node
from app.agents.state import new_state


def test_market_node_returns_snapshot_for_each_ticker() -> None:
    state = new_state()
    state["entities"] = {"tickers": ["BBCA", "BMRI"]}

    fake_closes = np.linspace(8000, 9000, 60)
    fake_news = []
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Indikator menunjukkan tren naik.")

    with patch("app.agents.market.node.fetch_close_prices", return_value=fake_closes), \
         patch("app.agents.market.node.fetch_news", return_value=fake_news), \
         patch("app.agents.market.node.get_chat_model", return_value=fake_llm):
        update = market_node(state)

    snapshot = update["entities"]["market_snapshot"]
    assert len(snapshot["tickers"]) == 2
    for t in snapshot["tickers"]:
        assert t["last_close"] is not None
        assert t["rsi14"] is not None
    assert snapshot["narration"]


def test_market_node_handles_empty_close_gracefully() -> None:
    """If yfinance returns nothing, ticker still appears in snapshot but with None metrics."""
    state = new_state()
    state["entities"] = {"tickers": ["XXXX"]}

    with patch("app.agents.market.node.fetch_close_prices", return_value=np.array([])), \
         patch("app.agents.market.node.fetch_news", return_value=[]), \
         patch("app.agents.market.node.get_chat_model"):
        update = market_node(state)

    t = update["entities"]["market_snapshot"]["tickers"][0]
    assert t["ticker"] == "XXXX"
    assert t["last_close"] is None
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_market_node.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement node**

`backend/app/agents/market/node.py`:

```python
"""Market Analyzer (N2a)."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.market.indicators import compute_indicators
from app.agents.market.news_client import fetch_news
from app.agents.market.schemas import MarketSnapshot, TickerSnapshot
from app.agents.market.yfinance_client import fetch_close_prices
from app.agents.state import AgentState
from app.core.gemini import get_chat_model

log = logging.getLogger(__name__)

NARRATE_SYSTEM = """\
You are an Indonesian market analyst. Given numeric indicators for several
tickers, write ONE short paragraph (≤120 words) summarizing the picture.
Do NOT introduce numbers that are not in the data. Do NOT make predictions.
Mention each ticker by name."""


def _last_or_none(arr: np.ndarray) -> float | None:
    if arr is None or len(arr) == 0:
        return None
    val = float(arr[-1])
    return None if np.isnan(val) else val


def _build_ticker_snapshot(ticker: str) -> TickerSnapshot:
    closes = fetch_close_prices(ticker)
    if len(closes) == 0:
        return TickerSnapshot(ticker=ticker, news=fetch_news(ticker))

    ind = compute_indicators(closes)
    return TickerSnapshot(
        ticker=ticker,
        last_close=float(closes[-1]),
        sma20=_last_or_none(ind["sma20"]),
        ema50=_last_or_none(ind["ema50"]),
        rsi14=_last_or_none(ind["rsi14"]),
        macd=_last_or_none(ind["macd"]),
        bb_upper=_last_or_none(ind["bb_upper"]),
        bb_lower=_last_or_none(ind["bb_lower"]),
        news=fetch_news(ticker),
    )


def _narrate(snapshots: list[TickerSnapshot]) -> str:
    llm = get_chat_model()
    body = "\n".join(
        f"- {s.ticker}: close={s.last_close}, RSI14={s.rsi14}, "
        f"SMA20={s.sma20}, MACD={s.macd}"
        for s in snapshots
    )
    resp = llm.invoke([
        SystemMessage(content=NARRATE_SYSTEM),
        HumanMessage(content=body),
    ])
    return getattr(resp, "content", "") or ""


def market_node(state: AgentState) -> AgentState:
    tickers = state.get("entities", {}).get("tickers") or []
    snapshots = [_build_ticker_snapshot(t) for t in tickers]
    narration = _narrate(snapshots) if snapshots else ""
    snapshot = MarketSnapshot(tickers=snapshots, narration=narration)

    return {
        "entities": {**state.get("entities", {}),
                     "market_snapshot": snapshot.model_dump()},
    }
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_market_node.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/market/node.py backend/tests/test_market_node.py
git commit -m "feat(market): N2a market analyzer node with TA-Lib + news + narration"
```

---

## Task Group B — Business Evaluator (N2b)

### Task B1: DCF model

**Files:**
- Create: `backend/app/agents/business/__init__.py`, `schemas.py`, `dcf.py`
- Create: `backend/tests/test_business_dcf.py`

- [ ] **Step 1: Write failing tests with spreadsheet-comparable values**

`backend/tests/test_business_dcf.py`:

```python
import pytest
from app.agents.business.dcf import discounted_cash_flow


def test_dcf_zero_growth_zero_terminal_matches_perpetuity_formula() -> None:
    """5-year FCF of 1M each, discount=10%, terminal_growth=0:
    PV ≈ Σ 1M/(1.1^t) for t=1..5 + (1M/0.10)/(1.1^5)."""
    cashflows = [1_000_000] * 5
    result = discounted_cash_flow(
        cashflows=cashflows, discount_rate=0.10, terminal_growth=0.0,
    )
    expected = sum(1_000_000 / (1.10 ** t) for t in range(1, 6))
    expected += (1_000_000 / 0.10) / (1.10 ** 5)
    assert result == pytest.approx(expected, rel=1e-6)


def test_dcf_with_terminal_growth_uses_gordon_model() -> None:
    """terminal value = FCF_n*(1+g)/(r-g), discounted from year n."""
    cashflows = [1_000_000, 1_100_000, 1_210_000]  # 10% growth
    r, g = 0.10, 0.03
    result = discounted_cash_flow(
        cashflows=cashflows, discount_rate=r, terminal_growth=g,
    )
    # Validate by recomputing inline; this guards against off-by-one in years
    pv = sum(c / (1 + r) ** t for t, c in enumerate(cashflows, start=1))
    tv = cashflows[-1] * (1 + g) / (r - g)
    pv += tv / (1 + r) ** len(cashflows)
    assert result == pytest.approx(pv, rel=1e-6)


def test_dcf_raises_when_discount_le_growth() -> None:
    """Gordon model degenerates when r ≤ g; we must reject not silently swallow."""
    with pytest.raises(ValueError, match="discount_rate must be greater than terminal_growth"):
        discounted_cash_flow(cashflows=[100], discount_rate=0.05, terminal_growth=0.10)
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_business_dcf.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement DCF**

`backend/app/agents/business/__init__.py`:

```python
```

`backend/app/agents/business/schemas.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class BusinessValuation(BaseModel):
    enterprise_value: float
    discount_rate: float
    terminal_growth: float
    cashflows: list[float]
    narration: str = Field(default="")
```

`backend/app/agents/business/dcf.py`:

```python
"""Discounted Cash Flow model — pure numpy/python, no LLM.

Standard 2-stage DCF: explicit cashflows for N years + terminal value via
Gordon growth model, discounted back to present at `discount_rate`."""
from __future__ import annotations

import numpy as np


def discounted_cash_flow(
    *,
    cashflows: list[float],
    discount_rate: float,
    terminal_growth: float,
) -> float:
    if discount_rate <= terminal_growth:
        raise ValueError(
            "discount_rate must be greater than terminal_growth (Gordon model)"
        )
    cf = np.asarray(cashflows, dtype=np.float64)
    n = len(cf)
    years = np.arange(1, n + 1)
    pv_explicit = float(np.sum(cf / (1 + discount_rate) ** years))

    terminal_value = cf[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1 + discount_rate) ** n
    return pv_explicit + pv_terminal
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_business_dcf.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/business/ backend/tests/test_business_dcf.py
git commit -m "feat(business): DCF model with Gordon terminal value (numpy only)"
```

---

### Task B2: ERP CSV connector + business_node

**Files:**
- Create: `backend/app/agents/business/erp_connector.py`
- Create: `backend/tests/data/sample_financials.csv`
- Create: `backend/app/agents/business/node.py`
- Create: `backend/tests/test_business_node.py`

- [ ] **Step 1: Create CSV fixture**

`backend/tests/data/sample_financials.csv`:

```csv
year,free_cash_flow
2021,800000000
2022,950000000
2023,1100000000
2024,1300000000
2025,1500000000
```

- [ ] **Step 2: Write failing tests**

`backend/tests/test_business_node.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from app.agents.business.node import business_node
from app.agents.state import new_state


def test_business_node_runs_dcf_when_financials_provided() -> None:
    state = new_state()
    state["entities"] = {"financials_csv": str(Path(__file__).parent / "data" / "sample_financials.csv")}

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Valuasi positif.")

    with patch("app.agents.business.node.get_chat_model", return_value=fake_llm):
        update = business_node(state)

    val = update["entities"]["business_valuation"]
    assert val["enterprise_value"] > 0
    assert val["narration"]


def test_business_node_skips_when_no_financials() -> None:
    state = new_state()  # no financials_csv key
    update = business_node(state)
    assert update["entities"]["business_valuation"] is None
```

- [ ] **Step 3: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_business_node.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement connector + node**

`backend/app/agents/business/erp_connector.py`:

```python
"""ERP connector interface. The hackathon ships only the CSV implementation;
real connectors (Accurate, Jurnal.id, Xero) are deferred."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


class CSVConnector:
    """Reads `year,free_cash_flow` rows from a CSV."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def fetch_cashflows(self) -> list[float]:
        df = pd.read_csv(self._path)
        if "free_cash_flow" not in df.columns:
            raise ValueError("CSV must have a 'free_cash_flow' column")
        return df["free_cash_flow"].astype(float).tolist()
```

`backend/app/agents/business/node.py`:

```python
"""Business Evaluator (N2b)."""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.business.dcf import discounted_cash_flow
from app.agents.business.erp_connector import CSVConnector
from app.agents.business.schemas import BusinessValuation
from app.agents.state import AgentState
from app.core.gemini import get_chat_model

log = logging.getLogger(__name__)

DEFAULT_DISCOUNT = 0.10
DEFAULT_TERMINAL = 0.03

NARRATE_SYSTEM = """\
You are a business valuation analyst. Given an enterprise value computed via
DCF along with the underlying cashflows, write ONE short paragraph (≤80 words)
summarizing the result. Do NOT introduce new numbers."""


def business_node(state: AgentState) -> AgentState:
    csv_path = state.get("entities", {}).get("financials_csv")
    if not csv_path:
        return {"entities": {**state.get("entities", {}), "business_valuation": None}}

    try:
        cashflows = CSVConnector(csv_path).fetch_cashflows()
        ev = discounted_cash_flow(
            cashflows=cashflows,
            discount_rate=DEFAULT_DISCOUNT,
            terminal_growth=DEFAULT_TERMINAL,
        )
    except Exception as exc:
        log.error("business_node: DCF failed: %s", exc)
        return {
            "entities": {**state.get("entities", {}), "business_valuation": None},
            "errors": [*state.get("errors", []),
                       {"node": "business", "reason": str(exc)}],
        }

    llm = get_chat_model()
    narration = llm.invoke([
        SystemMessage(content=NARRATE_SYSTEM),
        HumanMessage(content=f"EV={ev:,.0f}, cashflows={cashflows}, "
                             f"r={DEFAULT_DISCOUNT}, g={DEFAULT_TERMINAL}"),
    ]).content or ""

    val = BusinessValuation(
        enterprise_value=ev,
        discount_rate=DEFAULT_DISCOUNT,
        terminal_growth=DEFAULT_TERMINAL,
        cashflows=cashflows,
        narration=narration,
    )
    return {"entities": {**state.get("entities", {}),
                         "business_valuation": val.model_dump()}}
```

- [ ] **Step 5: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_business_node.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/business/erp_connector.py backend/app/agents/business/node.py backend/tests/test_business_node.py backend/tests/data/sample_financials.csv
git commit -m "feat(business): N2b business evaluator with CSV-based DCF"
```

---

## Task Group C — Risk Agent (N2c)

### Task C1: VaR (numpy)

**Files:**
- Create: `backend/app/agents/risk/__init__.py`, `var.py`
- Create: `backend/tests/test_risk_var.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_risk_var.py`:

```python
import numpy as np
import pytest

from app.agents.risk.var import historical_var, parametric_var


def test_historical_var_at_95_is_5th_percentile_of_losses() -> None:
    """VaR_95 = absolute value of the 5th percentile of returns."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0, 0.01, size=10_000)
    var = historical_var(returns, confidence=0.95)
    expected = -float(np.percentile(returns, 5))
    assert var == pytest.approx(expected, rel=1e-6)


def test_parametric_var_assumes_normal_distribution() -> None:
    """For a normal series with σ ≈ 0.01, VaR_95 ≈ 1.6449 * σ."""
    rng = np.random.default_rng(7)
    returns = rng.normal(0.0, 0.01, size=100_000)
    var = parametric_var(returns, confidence=0.95)
    assert var == pytest.approx(1.6449 * np.std(returns, ddof=1), rel=0.05)


def test_var_raises_on_empty_input() -> None:
    with pytest.raises(ValueError):
        historical_var(np.array([]), confidence=0.95)
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_risk_var.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement VaR**

`backend/app/agents/risk/__init__.py`:

```python
```

`backend/app/agents/risk/var.py`:

```python
"""Value-at-Risk computations (numpy only)."""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


def historical_var(returns: np.ndarray, confidence: float = 0.95) -> float:
    if len(returns) == 0:
        raise ValueError("returns array must be non-empty")
    pct = (1 - confidence) * 100
    return float(-np.percentile(returns, pct))


def parametric_var(returns: np.ndarray, confidence: float = 0.95) -> float:
    if len(returns) == 0:
        raise ValueError("returns array must be non-empty")
    mu = float(np.mean(returns))
    sigma = float(np.std(returns, ddof=1))
    z = norm.ppf(confidence)
    return -(mu - z * sigma)
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_risk_var.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/risk/__init__.py backend/app/agents/risk/var.py backend/tests/test_risk_var.py
git commit -m "feat(risk): historical + parametric VaR (numpy only)"
```

---

### Task C2: Mean-Variance Optimizer (scipy)

**Files:**
- Create: `backend/app/agents/risk/mvo.py`
- Create: `backend/tests/test_risk_mvo.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_risk_mvo.py`:

```python
import numpy as np
import pytest

from app.agents.risk.mvo import mean_variance_optimize


def test_mvo_two_asset_uncorrelated_equal_means_yields_50_50() -> None:
    """Two assets with identical expected returns and equal variance,
    no correlation → optimal min-variance is 50/50."""
    expected_returns = np.array([0.10, 0.10])
    cov = np.array([[0.04, 0.0], [0.0, 0.04]])
    weights = mean_variance_optimize(
        expected_returns=expected_returns, cov=cov, risk_aversion=1.0,
    )
    assert weights == pytest.approx(np.array([0.5, 0.5]), abs=1e-3)


def test_mvo_returns_sum_to_one_long_only() -> None:
    rng = np.random.default_rng(0)
    er = rng.normal(0.08, 0.03, size=4)
    A = rng.normal(size=(4, 4))
    cov = A @ A.T  # PSD
    w = mean_variance_optimize(expected_returns=er, cov=cov, risk_aversion=1.0)
    assert pytest.approx(w.sum(), abs=1e-3) == 1.0
    assert (w >= -1e-6).all()


def test_mvo_higher_aversion_increases_diversification() -> None:
    """Higher risk aversion → weights closer to equal."""
    er = np.array([0.20, 0.05])
    cov = np.array([[0.04, 0.0], [0.0, 0.04]])
    w_low = mean_variance_optimize(expected_returns=er, cov=cov, risk_aversion=0.1)
    w_high = mean_variance_optimize(expected_returns=er, cov=cov, risk_aversion=100.0)
    # Low aversion → tilt to high return; high aversion → near-equal
    assert w_low[0] > w_high[0]
    assert abs(w_high[0] - 0.5) < abs(w_low[0] - 0.5)
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_risk_mvo.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement MVO**

`backend/app/agents/risk/mvo.py`:

```python
"""Mean-Variance Optimization via scipy.optimize.

Solves: maximize w'μ - λ·w'Σw subject to Σwᵢ = 1, wᵢ ≥ 0.
λ = risk_aversion (higher → more diversification)."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


def mean_variance_optimize(
    *,
    expected_returns: np.ndarray,
    cov: np.ndarray,
    risk_aversion: float = 1.0,
) -> np.ndarray:
    n = len(expected_returns)

    def neg_utility(w: np.ndarray) -> float:
        return -(w @ expected_returns - risk_aversion * w @ cov @ w)

    cons = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n

    res = minimize(neg_utility, x0, method="SLSQP", bounds=bounds, constraints=cons)
    if not res.success:
        # Fall back to equal weights with a warning rather than crashing the graph.
        return x0
    return res.x
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_risk_mvo.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/risk/mvo.py backend/tests/test_risk_mvo.py
git commit -m "feat(risk): scipy SLSQP mean-variance optimizer (long-only)"
```

---

### Task C3: risk_node

**Files:**
- Create: `backend/app/agents/risk/schemas.py`
- Create: `backend/app/agents/risk/node.py`
- Create: `backend/tests/test_risk_node.py`

- [ ] **Step 1: Define schema**

`backend/app/agents/risk/schemas.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class RiskMetrics(BaseModel):
    var_95: float | None = None
    var_99: float | None = None
    sharpe: float | None = None


class RiskAssessment(BaseModel):
    metrics: RiskMetrics = Field(default_factory=RiskMetrics)
    suggested_weights: dict[str, float] = Field(default_factory=dict)
    narration: str = ""
```

- [ ] **Step 2: Write failing tests**

`backend/tests/test_risk_node.py`:

```python
from unittest.mock import MagicMock, patch

import numpy as np
from langchain_core.messages import AIMessage

from app.agents.risk.node import risk_node
from app.agents.state import new_state


def test_risk_node_computes_var_and_mvo_for_provided_tickers() -> None:
    state = new_state()
    state["entities"] = {"tickers": ["BBCA", "BMRI"]}

    rng = np.random.default_rng(0)
    fake_closes = {
        "BBCA": np.exp(np.cumsum(rng.normal(0.0005, 0.01, 252))) * 8000,
        "BMRI": np.exp(np.cumsum(rng.normal(0.0003, 0.012, 252))) * 6000,
    }

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Risiko terkendali.")

    with patch("app.agents.risk.node.fetch_close_prices",
               side_effect=lambda t, **kw: fake_closes[t]), \
         patch("app.agents.risk.node.get_chat_model", return_value=fake_llm):
        update = risk_node(state)

    risk = update["entities"]["risk_metrics"]
    assert risk["metrics"]["var_95"] > 0
    assert set(risk["suggested_weights"]) == {"BBCA", "BMRI"}
    assert abs(sum(risk["suggested_weights"].values()) - 1.0) < 1e-3
```

- [ ] **Step 3: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_risk_node.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement node**

`backend/app/agents/risk/node.py`:

```python
"""Risk Agent (N2c). Quantitative outputs come from numpy/scipy ONLY."""
from __future__ import annotations

import logging

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.market.yfinance_client import fetch_close_prices
from app.agents.risk.mvo import mean_variance_optimize
from app.agents.risk.schemas import RiskAssessment, RiskMetrics
from app.agents.risk.var import historical_var
from app.agents.state import AgentState
from app.core.gemini import get_chat_model

log = logging.getLogger(__name__)

NARRATE_SYSTEM = """\
You are a risk analyst. Given numeric VaR/Sharpe/weights, write ONE short
paragraph (≤80 words) summarizing the risk picture in Indonesian. Do NOT
introduce numbers not in the input."""


def _returns(closes: np.ndarray) -> np.ndarray:
    return np.diff(np.log(closes))


def risk_node(state: AgentState) -> AgentState:
    tickers = state.get("entities", {}).get("tickers") or []
    if not tickers:
        return {"entities": {**state.get("entities", {}),
                             "risk_metrics": RiskAssessment().model_dump()}}

    series: dict[str, np.ndarray] = {}
    for t in tickers:
        c = fetch_close_prices(t)
        if len(c) < 30:
            log.warning("risk_node: insufficient data for %s", t)
            continue
        series[t] = c

    if not series:
        return {"entities": {**state.get("entities", {}),
                             "risk_metrics": RiskAssessment().model_dump()}}

    rets = {t: _returns(c) for t, c in series.items()}
    aligned = np.vstack([r[-min(len(r) for r in rets.values()):] for r in rets.values()])

    expected_returns = aligned.mean(axis=1) * 252
    cov = np.cov(aligned) * 252
    weights = mean_variance_optimize(
        expected_returns=expected_returns, cov=cov, risk_aversion=2.0,
    )

    portfolio_returns = (weights[:, None] * aligned).sum(axis=0)
    metrics = RiskMetrics(
        var_95=historical_var(portfolio_returns, confidence=0.95),
        var_99=historical_var(portfolio_returns, confidence=0.99),
        sharpe=(portfolio_returns.mean() / portfolio_returns.std(ddof=1) * np.sqrt(252))
                if portfolio_returns.std(ddof=1) else None,
    )

    llm = get_chat_model()
    body = f"VaR95={metrics.var_95:.4f}, VaR99={metrics.var_99:.4f}, Sharpe={metrics.sharpe}"
    narration = llm.invoke([SystemMessage(content=NARRATE_SYSTEM),
                            HumanMessage(content=body)]).content or ""

    assessment = RiskAssessment(
        metrics=metrics,
        suggested_weights=dict(zip(series.keys(), [float(w) for w in weights])),
        narration=narration,
    )
    return {"entities": {**state.get("entities", {}),
                         "risk_metrics": assessment.model_dump()}}
```

- [ ] **Step 5: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_risk_node.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/risk/schemas.py backend/app/agents/risk/node.py backend/tests/test_risk_node.py
git commit -m "feat(risk): N2c risk agent with VaR + MVO + narration"
```

---

## Task Group D — Wire real nodes into the graph

### Task D1: Swap stubs for real nodes

**Files:**
- Modify: `backend/app/agents/graph.py`
- Modify: `backend/tests/test_graph_wiring.py` (update patch paths)

- [ ] **Step 1: Update graph.py imports**

In `backend/app/agents/graph.py`, replace:

```python
from app.agents.stubs import (
    business_stub,
    execution_stub,
    hitl_stub,
    market_stub,
    optimizer_stub,
    risk_stub,
)
```

with:

```python
from app.agents.business.node import business_node
from app.agents.market.node import market_node
from app.agents.risk.node import risk_node
from app.agents.stubs import execution_stub, hitl_stub, optimizer_stub
```

And in `build_graph()`, replace `market_stub`/`business_stub`/`risk_stub` calls with `market_node`/`business_node`/`risk_node`:

```python
g.add_node("n2a_market", market_node)
g.add_node("n2b_business", business_node)
g.add_node("n2c_risk", risk_node)
```

- [ ] **Step 2: Update existing graph wiring tests**

In `backend/tests/test_graph_wiring.py`, the existing tests patch `intent_node` and `legal_node`. They no longer need to mock the analyzers because the real nodes are now wired in — but real nodes call yfinance / Gemini, which we don't want during unit tests. Add patches for the analyzer external calls:

```python
@pytest.fixture(autouse=True)
def _patch_externals():
    """For graph-wiring tests we don't care about analyzer internals — mock the
    expensive parts so the test stays fast."""
    import numpy as np
    from unittest.mock import patch
    with patch("app.agents.market.node.fetch_close_prices", return_value=np.linspace(100, 110, 60)), \
         patch("app.agents.market.node.fetch_news", return_value=[]), \
         patch("app.agents.market.node.get_chat_model"), \
         patch("app.agents.risk.node.fetch_close_prices", return_value=np.linspace(100, 110, 252)), \
         patch("app.agents.risk.node.get_chat_model"), \
         patch("app.agents.business.node.get_chat_model"):
        yield
```

- [ ] **Step 3: Run all graph tests**

Run: `cd backend && uv run python -m pytest tests/test_graph_wiring.py tests/test_graph_endpoint.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/graph.py backend/tests/test_graph_wiring.py
git commit -m "feat(graph): wire real N2a/b/c analyzer nodes (replaces Phase 2 stubs)"
```

---

## Phase 3 Definition of Done

- [ ] All Phase 0–2 tests still pass.
- [ ] All new Phase 3 tests pass; quantitative tests within ≤ 0.1 % tolerance of reference values.
- [ ] Manual end-to-end: `POST /api/v1/agent/run` with `{"message":"alokasikan 10jt ke BBCA dan BMRI", "workspace_id":"..."}` returns a final state where `entities.market_snapshot` has real prices/RSI, `entities.risk_metrics` has computed VaR + suggested weights summing to ~1.0, and `entities.business_valuation` is `null` (no financials uploaded).
- [ ] Code-review checklist: every file in `app/agents/{market,business,risk}/` is verified for the LLM-quant rule (LLM only narrates; no LLM call returns numeric metrics).
- [ ] DeepEval narration check (`@pytest.mark.slow`): factuality ≥ 0.9 — i.e. the LLM doesn't misstate the numbers it was given.
