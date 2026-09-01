"""Hybrid stock recommendations: 50% Content-Based (technical score) +
50% User-Based (holdings-similarity collaborative filtering), with an
automatic cold-start fallback to 100% content-based when there isn't
enough comparable-workspace data. The A1-A4 verdict engine's own
`eligible_tickers` gate is applied to the full candidate set before
ranking, so a REJECT/AVOID-band ticker (e.g. a regulatory-sensitive
tobacco/alcohol name) never appears in the response at all. Deliberately
outside the LangGraph pipeline — read-only discovery, not a transaction
(see docs/superpowers/specs/2026-09-01-stock-recommendations-design.md)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agents.market.news_client import fetch_news
from app.agents.market.stock_engine import run_stock_engine
from app.agents.market.synthesizer import StockVerdict
from app.agents.market.yfinance_client import fetch_price_series_with_indicators
from app.agents.optimizer.sectors import TICKER_SECTOR, sector_of
from app.models.recommendations import RecommendationItem, RecommendationsResponse

log = logging.getLogger(__name__)


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
    data = fetch_price_series_with_indicators(ticker, period="6mo")
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


_MIN_COMPARABLE_WORKSPACES = 3


def user_scores(
    sb, workspace_id: str, candidate_tickers: list[str],
) -> tuple[dict[str, float], bool, str | None]:
    """Holdings-based collaborative filtering: how much workspaces with a
    similar sector-exposure profile favor each candidate ticker's sector.
    Returns (scores_by_ticker, personalized, fallback_reason) — scores is
    {} and personalized is False whenever there isn't enough comparable
    data (see the design spec's "Cold start" section)."""
    vectors = _sector_vectors_by_workspace(sb)
    my_vector = vectors.get(workspace_id)
    if not my_vector:
        return {}, False, "Workspace Anda belum memiliki histori kepemilikan saham."

    similarities: dict[str, float] = {}
    for other_id, vector in vectors.items():
        if other_id == workspace_id:
            continue
        sim = _cosine_similarity(my_vector, vector)
        if sim > 0.0:
            similarities[other_id] = sim

    if len(similarities) < _MIN_COMPARABLE_WORKSPACES:
        return {}, False, (
            f"Hanya menemukan {len(similarities)} workspace dengan profil kepemilikan "
            "mirip — terlalu sedikit untuk personalisasi."
        )

    total_similarity = sum(similarities.values())
    scores: dict[str, float] = {}
    for ticker in candidate_tickers:
        sector = sector_of(ticker)
        weighted = sum(
            similarities[other_id] * vectors[other_id].get(sector, 0.0)
            for other_id in similarities
        )
        scores[ticker] = 100.0 * weighted / total_similarity
    return scores, True, None


def _normalize_to_100(scores: dict[str, float]) -> dict[str, float]:
    """Min-max rescale to [0, 100] so this score sits on the same effective
    scale as content_score before a 50/50 blend. Without this, user_score
    (typically 0-35 for a diversified peer group) would be silently
    outweighed roughly 3:1 by content_score (which spans the full 0-100
    range) despite the stated 50/50 weighting."""
    if not scores:
        return {}
    values = list(scores.values())
    lo, hi = min(values), max(values)
    if hi == lo:
        neutral = 0.0 if hi == 0.0 else 50.0
        return {t: neutral for t in scores}
    return {t: 100.0 * (v - lo) / (hi - lo) for t, v in scores.items()}


_TOP_N_ENRICHED = 8


def build_recommendations(sb, workspace_id: str) -> RecommendationsResponse:
    """Full pipeline: content score every candidate -> holdings-based user
    score (or cold-start fallback) -> 50/50 hybrid blend -> A1-A4 verdict
    for every viable candidate -> filter to the engine's own
    eligible_tickers (REJECT/AVOID band excluded entirely, not just
    unbadged — a compliance requirement, since eligible_tickers is what
    keeps a REJECT-band tobacco/alcohol stock, or any manipulation/gate
    failure, off a page titled "worth buying") -> rank the eligible set ->
    keep the verdict field only for the top _TOP_N_ENRICHED of that
    ranking (payload-size control only; verdicts for the rest of the
    eligible set were already computed but are dropped from the response).

    Fails closed: if verdict enrichment itself raises, eligibility can't be
    determined at all, so this returns zero recommendations rather than
    falling back to an unfiltered (and therefore unvetted) list."""
    content_scores: dict[str, float] = {}
    for ticker in TICKER_SECTOR:
        score = content_score_for(ticker)
        if score is not None:
            content_scores[ticker] = score

    if len(content_scores) < len(TICKER_SECTOR):
        log.info(
            "recommendations: %d/%d candidate tickers had usable technical data",
            len(content_scores), len(TICKER_SECTOR),
        )

    viable = list(content_scores.keys())
    raw_user_scores, personalized, fallback_reason = user_scores(sb, workspace_id, viable)
    user_score_map = _normalize_to_100(raw_user_scores) if personalized else raw_user_scores

    hybrid_scores: dict[str, float] = {}
    for ticker in viable:
        content = content_scores[ticker]
        if personalized:
            hybrid_scores[ticker] = 0.5 * content + 0.5 * user_score_map.get(ticker, 0.0)
        else:
            hybrid_scores[ticker] = content

    verdicts: dict[str, StockVerdict] = {}
    eligible_tickers: set[str] = set()
    if viable:
        try:
            engine = run_stock_engine(viable, news_by_ticker={t: fetch_news(t) for t in viable})
            verdicts = {t: StockVerdict(**v) for t, v in engine["verdicts"].items()}
            eligible_tickers = set(engine["eligible_tickers"])
        except Exception as exc:
            log.warning(
                "recommendations: verdict enrichment failed, returning no candidates: %s", exc
            )

    eligible = [t for t in viable if t in eligible_tickers]
    ranked = sorted(eligible, key=lambda t: hybrid_scores[t], reverse=True)
    top_n_tickers = set(ranked[:_TOP_N_ENRICHED])

    items = [
        RecommendationItem(
            ticker=ticker,
            sector=sector_of(ticker),
            rank=i + 1,
            content_score=round(content_scores[ticker], 1),
            user_score=round(user_score_map.get(ticker, 0.0), 1),
            hybrid_score=round(hybrid_scores[ticker], 1),
            verdict=verdicts.get(ticker) if ticker in top_n_tickers else None,
        )
        for i, ticker in enumerate(ranked)
    ]

    return RecommendationsResponse(
        workspace_id=workspace_id,
        personalized=personalized,
        fallback_reason=fallback_reason,
        items=items,
        as_of=datetime.now(timezone.utc).isoformat(),
    )
