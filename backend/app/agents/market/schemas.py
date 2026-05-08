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
