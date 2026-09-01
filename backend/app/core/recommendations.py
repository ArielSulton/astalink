"""Hybrid stock recommendations: 50% Content-Based (technical score) +
50% User-Based (holdings-similarity collaborative filtering), with an
automatic cold-start fallback to 100% content-based when there isn't
enough comparable-workspace data. Deliberately outside the LangGraph
pipeline — read-only discovery, not a transaction (see
docs/superpowers/specs/2026-09-01-stock-recommendations-design.md)."""
from __future__ import annotations

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
