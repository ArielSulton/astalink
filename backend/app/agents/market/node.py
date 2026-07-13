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
from app.core.gemini import extract_text, get_chat_model
from app.core.metrics import track_node_duration

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
    return extract_text(getattr(resp, "content", ""))


@track_node_duration("n2a_market")
def market_node(state: AgentState) -> AgentState:
    entities = state.get("entities", {})
    tickers = entities.get("tickers") or []
    snapshots = [_build_ticker_snapshot(t) for t in tickers]
    narration = _narrate(snapshots) if snapshots else ""
    snapshot = MarketSnapshot(tickers=snapshots, narration=narration)

    update = {"market_snapshot": snapshot.model_dump()}

    # Layer 1 stock engine (A1-A4 + synthesizer) — only when Layer 0 already
    # allocated >0% to stocks (this node isn't reached otherwise for
    # allocation intents). Verdict REJECT/AVOID tickers are excluded from the
    # optimizer via eligible_tickers.
    if state.get("layer0_result"):
        from app.agents.market.stock_engine import run_stock_engine

        try:
            amount = float(entities.get("amount") or 0) or None
        except (TypeError, ValueError):
            amount = None
        try:
            engine = run_stock_engine(
                tickers,
                news_by_ticker={s.ticker: s.news for s in snapshots},
                total_amount_idr=amount,
            )
            update["stock_engine"] = engine
            update["eligible_tickers"] = engine["eligible_tickers"]
        except Exception as exc:
            log.error("market_node: stock engine failed: %s", exc)

    return {"entities": {**entities, **update}}
