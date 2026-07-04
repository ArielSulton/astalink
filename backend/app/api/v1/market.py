"""Market watchlist endpoint — returns price series + indicators for a set of tickers."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.agents.market.news_client import fetch_news
from app.agents.market.schemas import NewsItem
from app.agents.market.yfinance_client import fetch_price_series_with_indicators

router = APIRouter()

DEFAULT_TICKERS = "BBCA.JK,TLKM.JK,ASII.JK,BBRI.JK"


class PricePoint(BaseModel):
    date: str
    close: float
    sma20: float | None = None
    ema50: float | None = None
    rsi14: float | None = None


class TickerChartData(BaseModel):
    ticker: str
    last_close: float | None = None
    prev_close: float | None = None
    price_change_pct: float | None = None
    rsi14: float | None = None
    sma20: float | None = None
    macd: float | None = None
    bb_upper: float | None = None
    bb_lower: float | None = None
    price_series: list[PricePoint] = []


class NewsResponse(BaseModel):
    ticker: str
    articles: list[NewsItem]


@router.get("/watchlist", response_model=list[TickerChartData])
async def get_watchlist(
    tickers: str = Query(default=DEFAULT_TICKERS, description="Comma-separated ticker symbols"),
) -> list[TickerChartData]:
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()][:10]
    result: list[TickerChartData] = []

    for ticker in ticker_list:
        data = fetch_price_series_with_indicators(ticker)

        last_close = data["last_close"]
        prev_close = data["prev_close"]
        change_pct: float | None = None
        if last_close is not None and prev_close is not None and prev_close != 0:
            change_pct = (last_close - prev_close) / prev_close * 100

        result.append(
            TickerChartData(
                ticker=ticker,
                last_close=last_close,
                prev_close=prev_close,
                price_change_pct=change_pct,
                rsi14=data["rsi14"],
                sma20=data["sma20"],
                macd=data["macd"],
                bb_upper=data["bb_upper"],
                bb_lower=data["bb_lower"],
                price_series=[PricePoint(**p) for p in data["series"]],
            )
        )

    return result


@router.get("/news", response_model=NewsResponse)
async def get_ticker_news(
    ticker: str = Query(default="BBCA.JK", description="Single IDX ticker symbol"),
) -> NewsResponse:
    # fetch_news is sync (uses httpx.get + Gemini) — run in thread pool
    articles = await asyncio.to_thread(fetch_news, ticker, 12)
    return NewsResponse(ticker=ticker, articles=articles)
