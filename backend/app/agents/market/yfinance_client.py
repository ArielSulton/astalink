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
