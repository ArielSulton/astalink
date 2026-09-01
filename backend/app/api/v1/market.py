"""Market watchlist + chart endpoints — price/indicator series over a period/interval."""
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
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    sma20: float | None = None
    ema9: float | None = None
    ema20: float | None = None
    ema50: float | None = None
    vwap: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    rsi14: float | None = None
    atr14: float | None = None
    stoch_k: float | None = None
    stoch_d: float | None = None
    obv: float | None = None


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


def _build_chart_data(ticker: str, period: str, interval: str) -> TickerChartData:
    data = fetch_price_series_with_indicators(ticker, period=period, interval=interval)

    last_close = data["last_close"]
    prev_close = data["prev_close"]
    change_pct: float | None = None
    if last_close is not None and prev_close is not None and prev_close != 0:
        change_pct = (last_close - prev_close) / prev_close * 100

    return TickerChartData(
        ticker=ticker,
        last_close=last_close,
        prev_close=prev_close,
        price_change_pct=change_pct,
        rsi14=data.get("rsi14"),
        sma20=data.get("sma20"),
        macd=data.get("macd"),
        bb_upper=data.get("bb_upper"),
        bb_lower=data.get("bb_lower"),
        price_series=[PricePoint(**p) for p in data["series"]],
    )


@router.get("/watchlist", response_model=list[TickerChartData])
async def get_watchlist(
    tickers: str = Query(default=DEFAULT_TICKERS, description="Comma-separated ticker symbols"),
    period: str = Query(default="1mo", description="yfinance period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max"),
    interval: str = Query(default="1d", description="yfinance interval: 1m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo"),
) -> list[TickerChartData]:
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()][:10]
    return [_build_chart_data(t, period, interval) for t in ticker_list]


@router.get("/chart", response_model=TickerChartData)
async def get_chart(
    ticker: str = Query(default="BBCA.JK", description="Single IDX ticker symbol"),
    period: str = Query(default="1mo", description="yfinance period"),
    interval: str = Query(default="1d", description="yfinance interval"),
) -> TickerChartData:
    return _build_chart_data(ticker, period, interval)


@router.get("/news", response_model=NewsResponse)
async def get_ticker_news(
    ticker: str = Query(default="BBCA.JK", description="Single IDX ticker symbol"),
) -> NewsResponse:
    articles = await asyncio.to_thread(fetch_news, ticker, 12)
    return NewsResponse(ticker=ticker, articles=articles)