"""Layer 1 stock engine — runs A1-A4 in parallel per ticker + synthesizer.

Called from the market node (N2a) for allocation intents. The four analyses
are independent I/O-bound fetches, so they run concurrently on a thread
pool — this is the repo's mapping of "A1-A4 run in parallel" onto a single
LangGraph node (adding four graph nodes would only buy the same concurrency
at the cost of four more state reducers).

Output per ticker is a StockVerdict; tickers whose verdict band is REJECT
(hard A3 gate / manipulation) or AVOID never reach the optimizer — the
engine also emits `eligible_tickers` for downstream consumption.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.agents.market.flow import FlowScore, fetch_flow_score
from app.agents.market.gate import GateResult, evaluate_gate, fetch_liquidity_data
from app.agents.market.macro import MacroScore, fetch_macro_score
from app.agents.market.news_scoring import NewsScore, enrich_news, score_news
from app.agents.market.schemas import NewsItem
from app.agents.market.synthesizer import StockVerdict, VerdictBand, synthesize
from app.agents.market.yfinance_client import fetch_price_series_with_indicators

log = logging.getLogger(__name__)

_ELIGIBLE_BANDS = {VerdictBand.STRONG_BUY, VerdictBand.BUY, VerdictBand.WATCHLIST}


def _analyze_ticker(ticker: str, news_items: list[NewsItem],
                    macro: MacroScore, position_idr: float | None) -> StockVerdict:
    as_of = datetime.now(timezone.utc).isoformat()

    series = fetch_price_series_with_indicators(ticker)
    dated_closes = [(p["date"], p["close"]) for p in series.get("series", [])]
    last_close = series.get("last_close")

    enriched = enrich_news(news_items, dated_closes)
    news_score: NewsScore = score_news(enriched, as_of=as_of)

    has_news = any(i.credibility in ("primary", "secondary") for i in enriched)
    gate: GateResult = evaluate_gate(
        fetch_liquidity_data(ticker, has_recent_fundamental_news=has_news),
        planned_position_idr=position_idr)

    flow: FlowScore = fetch_flow_score(ticker)

    return synthesize(ticker, news_score, macro, gate, flow,
                      last_close=last_close, as_of=as_of)


def run_stock_engine(
    tickers: list[str],
    news_by_ticker: dict[str, list[NewsItem]],
    total_amount_idr: float | None = None,
) -> dict:
    """Returns {"verdicts": {ticker: verdict_dump}, "eligible_tickers": [...],
    "macro": macro_dump, "as_of": iso}."""
    macro = fetch_macro_score()   # once, shared by every ticker
    position = (total_amount_idr / len(tickers)
                if total_amount_idr and tickers else None)

    verdicts: dict[str, StockVerdict] = {}
    if tickers:
        with ThreadPoolExecutor(max_workers=min(4, len(tickers))) as pool:
            futures = {
                t: pool.submit(_analyze_ticker, t,
                               news_by_ticker.get(t, []), macro, position)
                for t in tickers
            }
            for t, fut in futures.items():
                try:
                    verdicts[t] = fut.result()
                except Exception as exc:
                    log.error("stock_engine: %s failed: %s", t, exc)

    eligible = [t for t, v in verdicts.items() if v.band in _ELIGIBLE_BANDS]
    return {
        "verdicts": {t: v.model_dump() for t, v in verdicts.items()},
        "eligible_tickers": eligible,
        "macro": macro.model_dump(),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
