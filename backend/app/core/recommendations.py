"""Hybrid stock recommendations: 50% Content-Based (technical score) +
50% User-Based (holdings-similarity collaborative filtering), with an
automatic cold-start fallback to 100% content-based when there isn't
enough comparable-workspace data. Deliberately outside the LangGraph
pipeline — read-only discovery, not a transaction (see
docs/superpowers/specs/2026-09-01-stock-recommendations-design.md)."""
from __future__ import annotations

from app.agents.market.yfinance_client import fetch_price_series_with_indicators
from app.agents.optimizer.sectors import sector_of


def _bare_ticker(ticker: str) -> str:
    """Strip a Yahoo-style exchange suffix (e.g. "BBCA.JK" -> "BBCA").
    `holdings.ticker` rows are stored suffixed; `TICKER_SECTOR` keys are
    bare — see the design spec's "Ticker universe & normalization" section."""
    return ticker.split(".")[0].upper()


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    norm_a = sum(v * v for v in a.values()) ** 0.5
    norm_b = sum(v * v for v in b.values()) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _sector_vectors_by_workspace(sb) -> dict[str, dict[str, float]]:
    """One query for every workspace's normalized sector-exposure vector
    (cost-basis weighted), keyed by workspace_id. Workspaces with zero net
    exposure (no holdings, or a data anomaly summing to 0) are omitted."""
    rows = (
        sb.table("holdings").select("workspace_id,ticker,quantity,avg_cost").execute()
    ).data or []

    raw: dict[str, dict[str, float]] = {}
    for r in rows:
        sector = sector_of(_bare_ticker(r["ticker"]))
        value = float(r["quantity"]) * float(r["avg_cost"])
        bucket = raw.setdefault(r["workspace_id"], {})
        bucket[sector] = bucket.get(sector, 0.0) + value

    vectors: dict[str, dict[str, float]] = {}
    for workspace_id, exposure in raw.items():
        total = sum(exposure.values())
        if total > 0:
            vectors[workspace_id] = {k: v / total for k, v in exposure.items()}
    return vectors


_CHECK_MAX = 25.0


def _rsi_zone_score(rsi14: float) -> float:
    """1.0 in the 45-70 "healthy" band, tapering linearly to 0.0 at the
    20/85 extremes on either side."""
    if 45.0 <= rsi14 <= 70.0:
        return 1.0
    if 20.0 < rsi14 < 45.0:
        return (rsi14 - 20.0) / (45.0 - 20.0)
    if 70.0 < rsi14 < 85.0:
        return (85.0 - rsi14) / (85.0 - 70.0)
    return 0.0


def _trend_check(last_close: float | None, sma20: float | None) -> float | None:
    if last_close is None or sma20 is None:
        return None
    return _CHECK_MAX if last_close > sma20 else 0.0


def _macd_check(macd: float | None) -> float | None:
    if macd is None:
        return None
    return _CHECK_MAX if macd > 0 else 0.0


def _bollinger_check(last_close: float | None, bb_upper: float | None) -> float | None:
    if last_close is None or bb_upper is None:
        return None
    return _CHECK_MAX if last_close < bb_upper else 0.0


def content_score_for(ticker: str) -> float | None:
    """Technical-only quality score (0-100) using only the top-level
    fields `fetch_price_series_with_indicators` guarantees on its success
    path: last_close, sma20, rsi14, macd (the MACD *line*, not the
    histogram — see the design spec), bb_upper. A single missing field
    excludes that check and renormalizes over the rest; returns None only
    when every check is unavailable (so the caller can drop the ticker
    entirely rather than score it as 0)."""
    data = fetch_price_series_with_indicators(ticker)
    last_close = data.get("last_close")
    rsi14 = data.get("rsi14")

    checks: list[float | None] = [
        _trend_check(last_close, data.get("sma20")),
        _CHECK_MAX * _rsi_zone_score(rsi14) if rsi14 is not None else None,
        _macd_check(data.get("macd")),
        _bollinger_check(last_close, data.get("bb_upper")),
    ]
    known = [c for c in checks if c is not None]
    if not known:
        return None
    return (sum(known) / len(known)) * (100.0 / _CHECK_MAX)
