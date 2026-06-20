"""Market watchlist endpoint — returns price series + indicators for a set of tickers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.agents.market.yfinance_client import fetch_price_series_with_indicators
from app.api.deps import get_current_user

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


@router.get("/watchlist", response_model=list[TickerChartData])
async def get_watchlist(
    tickers: str = Query(default=DEFAULT_TICKERS, description="Comma-separated ticker symbols"),
    user: dict = Depends(get_current_user),
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
