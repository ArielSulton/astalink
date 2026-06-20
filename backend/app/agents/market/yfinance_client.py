"""yfinance wrapper. Returns numpy close-price arrays.

We call yfinance lazily and cache per-ticker to avoid hammering the API during
hot-reload dev cycles. Cache TTL is 5 minutes — balance between freshness and
not getting rate-limited."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import numpy as np
import yfinance as yf

log = logging.getLogger(__name__)

_CACHE_TTL = 300  # seconds


@dataclass
class _CacheEntry:
    closes: np.ndarray
    fetched_at: float


_cache: dict[str, _CacheEntry] = {}


@dataclass
class _SeriesCacheEntry:
    data: dict
    fetched_at: float


_series_cache: dict[str, _SeriesCacheEntry] = {}


def fetch_price_series_with_indicators(ticker: str, window: int = 90) -> dict:
    """Return `window` trading days of OHLCV + precomputed indicators.

    Fetches 1 year so SMA20/EMA50 are properly warmed before the returned window.
    Returns a dict with keys: series, last_close, prev_close, rsi14, sma20, macd,
    bb_upper, bb_lower.  Any uncomputable value is None.
    """
    cache_key = f"series:{ticker}"
    now = time.time()
    if (entry := _series_cache.get(cache_key)) and now - entry.fetched_at < _CACHE_TTL:
        return entry.data

    from app.agents.market.indicators import compute_indicators  # lazy: avoids TA-Lib at import time

    try:
        df = yf.Ticker(ticker).history(period="1y", auto_adjust=True)
    except Exception as exc:
        log.error("yfinance price_series: failed for %s: %s", ticker, exc)
        return {"series": [], "last_close": None, "prev_close": None,
                "rsi14": None, "sma20": None, "macd": None, "bb_upper": None, "bb_lower": None}

    if df.empty or len(df) < 2:
        return {"series": [], "last_close": None, "prev_close": None,
                "rsi14": None, "sma20": None, "macd": None, "bb_upper": None, "bb_lower": None}

    closes = df["Close"].to_numpy().astype(np.float64)
    dates = [str(idx.date()) for idx in df.index]

    try:
        ind = compute_indicators(closes)
    except Exception as exc:
        log.error("yfinance price_series: indicators failed for %s: %s", ticker, exc)
        ind = {}

    def _float_or_none(arr: "np.ndarray | None", i: int) -> "float | None":
        if arr is None or len(arr) == 0:
            return None
        v = float(arr[i])
        return None if (v != v) else v  # NaN check

    start = max(0, len(closes) - window)
    series = [
        {
            "date": dates[i],
            "close": float(closes[i]),
            "sma20": _float_or_none(ind.get("sma20"), i),
            "ema50": _float_or_none(ind.get("ema50"), i),
            "rsi14": _float_or_none(ind.get("rsi14"), i),
        }
        for i in range(start, len(closes))
    ]

    def _last(key: str) -> "float | None":
        return _float_or_none(ind.get(key), -1) if ind else None

    result = {
        "series": series,
        "last_close": float(closes[-1]),
        "prev_close": float(closes[-2]),
        "rsi14": _last("rsi14"),
        "sma20": _last("sma20"),
        "macd": _last("macd"),
        "bb_upper": _last("bb_upper"),
        "bb_lower": _last("bb_lower"),
    }
    _series_cache[cache_key] = _SeriesCacheEntry(data=result, fetched_at=time.time())
    return result


def fetch_close_prices(ticker: str, period: str = "1y") -> np.ndarray:
    now = time.time()
    if (entry := _cache.get(ticker)) and now - entry.fetched_at < _CACHE_TTL:
        return entry.closes

    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    except Exception as exc:
        log.error("yfinance: fetch failed for %s: %s", ticker, exc)
        return np.array([])

    if df.empty:
        log.warning("yfinance: empty history for %s", ticker)
        return np.array([])

    closes = df["Close"].to_numpy()
    _cache[ticker] = _CacheEntry(closes=closes, fetched_at=now)
    return closes
