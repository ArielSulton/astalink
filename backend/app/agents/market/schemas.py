from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Sentiment = Literal["positive", "neutral", "negative"]

# A1 credibility ladder (folded-in hard gate — see market/news_scoring.py):
# PRIMARY = IDX official disclosure, SECONDARY = mainstream media,
# RUMOR = forum / social / unattributed.
Credibility = Literal["primary", "secondary", "rumor"]


class NewsItem(BaseModel):
    title: str
    source: str
    published_at: str
    sentiment: Sentiment
    credibility: Credibility = "rumor"
    # True when the price already moved >threshold BEFORE publication —
    # the news is lagging, not a catalyst.
    already_priced_in: bool = False
    # True when one positive story is replicated across many low-quality
    # outlets within a short window.
    coordinated_amplification: bool = False


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
