"""A1 — News & Sentiment scoring, with the folded-in adversarial gates.

Three checks that used to be a standalone adversarial agent now live here
as plain fields, computed rule-based with NO additional model calls:

- credibility: PRIMARY (IDX disclosure) / SECONDARY (mainstream media) /
  RUMOR (forum, social, unattributed). Weighting comes from config
  (primary ≈ 3× secondary ≈ 6× rumor).
- already_priced_in: the price moved more than the configured threshold
  BEFORE publication → the story is lagging, not a catalyst → it
  contributes nothing to the score.
- coordinated_amplification: the same positive story replicated across
  several low-quality outlets inside a short window → the copies count as
  ONE rumor-grade item, not many.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from app.agents.market.schemas import Credibility, NewsItem
from app.core.allocation_config import allocation_config

log = logging.getLogger(__name__)

# Source classification (case-insensitive substring match).
_PRIMARY_SOURCES = ("idx.co.id", "bursa efek", "keterbukaan informasi", "idx ")
_SECONDARY_SOURCES = (
    "kompas", "detik", "bisnis.com", "bisnis indonesia", "kontan", "cnbc",
    "cnn", "tempo", "katadata", "reuters", "bloomberg", "antara", "investor.id",
    "liputan6", "kumparan", "the jakarta post", "jakarta globe", "emitennews",
    "idn financials", "idnfinancials",
)


class NewsScore(BaseModel):
    """A1 output for one ticker. Score 0-100; 50 = neutral."""
    score: float | None = None    # None when there is no scorable news
    n_items: int = 0
    n_priced_in: int = 0
    n_amplified: int = 0
    detail: list[str] = Field(default_factory=list)
    as_of: str = ""


def classify_credibility(source: str) -> Credibility:
    s = (source or "").lower()
    if any(k in s for k in _PRIMARY_SOURCES):
        return "primary"
    if any(k in s for k in _SECONDARY_SOURCES):
        return "secondary"
    return "rumor"


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def detect_priced_in(published_at: str,
                     dated_closes: list[tuple[str, float]]) -> bool:
    """True if the close moved more than the configured threshold within
    the lookback window BEFORE the publication date."""
    cfg = allocation_config.news
    pub = _parse_dt(published_at)
    if pub is None or len(dated_closes) < 2:
        return False
    pub_date = pub.date()
    window_start = pub_date - timedelta(days=cfg.priced_in_lookback_days)
    window = [c for d, c in dated_closes
              if (dt := _parse_dt(d)) and window_start <= dt.date() <= pub_date]
    if len(window) < 2 or window[0] == 0:
        return False
    move = abs(window[-1] - window[0]) / window[0]
    return move > cfg.priced_in_move_pct


def _title_tokens(title: str) -> set[str]:
    return {w for w in title.lower().split() if len(w) > 3}


def detect_amplification(items: list[NewsItem]) -> set[int]:
    """Indices of items that are copies of the same positive story spread
    across low-quality outlets within the window. The FIRST occurrence is
    not marked — only its copies."""
    cfg = allocation_config.news
    marked: set[int] = set()
    for i, a in enumerate(items):
        if i in marked or a.sentiment != "positive":
            continue
        a_dt, a_tok = _parse_dt(a.published_at), _title_tokens(a.title)
        if a_dt is None or not a_tok:
            continue
        copies = [i]
        for j in range(i + 1, len(items)):
            b = items[j]
            if b.sentiment != "positive" or b.credibility == "primary":
                continue
            b_dt = _parse_dt(b.published_at)
            if b_dt is None or abs((b_dt - a_dt).total_seconds()) > \
                    cfg.amplification_window_hours * 3600:
                continue
            b_tok = _title_tokens(b.title)
            if not b_tok:
                continue
            jaccard = len(a_tok & b_tok) / len(a_tok | b_tok)
            if jaccard >= 0.5:
                copies.append(j)
        if len(copies) >= cfg.amplification_min_copies:
            marked.update(copies[1:])   # keep the original, mark the echo
    return marked


def enrich_news(items: list[NewsItem],
                dated_closes: list[tuple[str, float]] | None = None) -> list[NewsItem]:
    """Fill credibility / already_priced_in / coordinated_amplification."""
    enriched = [
        item.model_copy(update={
            "credibility": classify_credibility(item.source),
            "already_priced_in": detect_priced_in(item.published_at,
                                                  dated_closes or []),
        })
        for item in items
    ]
    for idx in detect_amplification(enriched):
        enriched[idx] = enriched[idx].model_copy(
            update={"coordinated_amplification": True})
    return enriched


def score_news(items: list[NewsItem], as_of: str = "") -> NewsScore:
    """Credibility-weighted sentiment → 0-100 (50 neutral).

    priced-in items contribute nothing; amplified copies are downgraded to
    a single rumor-weight voice (their originals still count once)."""
    cfg = allocation_config.news
    weight_by_cred = {"primary": cfg.weight_primary,
                      "secondary": cfg.weight_secondary,
                      "rumor": cfg.weight_rumor}
    sentiment_value = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}

    detail: list[str] = []
    total_w = signed = 0.0
    n_priced = n_amp = 0
    for item in items:
        if item.already_priced_in:
            n_priced += 1
            detail.append(f"Priced-in (diabaikan): {item.title[:60]}")
            continue
        if item.coordinated_amplification:
            n_amp += 1
            detail.append(f"Amplifikasi terkoordinasi (diabaikan): {item.title[:60]}")
            continue
        w = weight_by_cred[item.credibility]
        total_w += w
        signed += w * sentiment_value[item.sentiment]

    score = None if total_w == 0 else 50.0 + 50.0 * (signed / total_w)
    return NewsScore(score=score, n_items=len(items), n_priced_in=n_priced,
                     n_amplified=n_amp, detail=detail, as_of=as_of)
