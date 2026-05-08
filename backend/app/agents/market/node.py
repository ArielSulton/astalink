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
