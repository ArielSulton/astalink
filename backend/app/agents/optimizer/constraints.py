"""Translate Legal Agent feedback into solver constraints.

Citations may carry an explicit `forbidden_tickers` metadata field (set by the
Legal node when it identifies banned instruments) or only a span of regulatory
text — for the latter we apply heuristic keyword → sector mapping."""
from __future__ import annotations

from typing import Any

# Indonesian regulatory keywords → sector tags. Hackathon-quality; fine-tune
# based on Phase 1 retrieval results.
KEYWORD_SECTOR = {
    "rokok": "tobacco",
    "tembakau": "tobacco",
    "alkohol": "alcohol",
    "miras": "alcohol",
    "judi": "gambling",
}


def forbidden_from_citations(citations: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for c in citations:
        out.extend(c.get("forbidden_tickers", []))
    # Preserve order, dedupe.
    seen: set[str] = set()
    return [t for t in out if not (t in seen or seen.add(t))]


def partial_tickers_from_citations(citations: list[dict[str, Any]]) -> dict[str, float]:
    """Merge per-citation partial-weight caps. When multiple citations cap
    the same ticker differently, the stricter (lower) cap wins — legal
    constraints tighten, they never get relaxed by picking the looser rule."""
    caps: dict[str, float] = {}
    for c in citations:
        for ticker, cap in (c.get("partial_tickers") or {}).items():
            if ticker not in caps or cap < caps[ticker]:
                caps[ticker] = cap
    return caps


def sector_caps_from_citations(citations: list[dict[str, Any]]) -> dict[str, float]:
    caps: dict[str, float] = {}
    for c in citations:
        span = (c.get("span") or "").lower()
        for keyword, sector in KEYWORD_SECTOR.items():
            if keyword in span:
                caps[sector] = 0.0
    return caps
