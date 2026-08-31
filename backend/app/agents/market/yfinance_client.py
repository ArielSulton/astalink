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


def _normalize_idx_ticker(ticker: str) -> str:
    """IDX-listed tickers need a .JK suffix on Yahoo Finance. A bare code
    like "BBCA" doesn't 404 — it silently resolves to an unrelated foreign
    symbol on a different exchange, which is worse than a crash (wrong price
    data, no error). AstaLink is IDX-only (OJK/UUPM compliance scope), so any
    ticker without an exchange suffix is assumed to be one; codes that
    already carry a suffix (e.g. "BBCA.JK") are left untouched."""
    return ticker if "." in ticker else f"{ticker}.JK"


def fetch_price_series_with_indicators(
    ticker: str,
    period: str = "1mo",
    interval: str = "1d",
    window: int | None = None,
) -> dict:
    """Return OHLCV + precomputed indicators for a ticker over a yfinance period/interval.

    Fetches `period` (e.g. "1y") at `interval` (e.g. "1d") and computes the full
    indicator pack. If `window` is set, only the trailing `window` data points are
    returned (the fetch still uses `period` for indicator warm-up); if None, the full
    series is returned. Returns a dict with keys: series, last_close, prev_close,
    rsi14, sma20, macd, bb_upper, bb_lower. Any uncomputable value is None.
    """
    ticker = _normalize_idx_ticker(ticker)
    cache_key = f"series:{ticker}:{period}:{interval}"
    now = time.time()
    if (entry := _series_cache.get(cache_key)) and now - entry.fetched_at < _CACHE_TTL:
        return entry.data

    from app.agents.market.indicators import compute_indicators  # lazy: avoids TA-Lib at import time

    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        # Drop still-open-session rows (NaN Close) so they don't pollute indicators.
        df = df[df["Close"].notna()]
    except Exception as exc:
        log.error("yfinance price_series: failed for %s: %s", ticker, exc)
        return {"series": [], "last_close": None, "prev_close": None,
                "rsi14": None, "sma20": None, "macd": None, "bb_upper": None, "bb_lower": None,
                **{k: None for k in ("bb_middle", "macd_signal", "macd_hist", "atr14",
                                     "stoch_k", "stoch_d", "obv", "vwap", "ema9", "ema20")}}

    if df.empty or len(df) < 2:
        return {"series": [], "last_close": None, "prev_close": None,
                "rsi14": None, "sma20": None, "macd": None, "bb_upper": None, "bb_lower": None,
                **{k: None for k in ("bb_middle", "macd_signal", "macd_hist", "atr14",
                                     "stoch_k", "stoch_d", "obv", "vwap", "ema9", "ema20")}}

    closes = df["Close"].to_numpy().astype(np.float64)
    highs = df["High"].to_numpy().astype(np.float64)
    lows = df["Low"].to_numpy().astype(np.float64)
    opens = df["Open"].to_numpy().astype(np.float64)
    volumes = df["Volume"].to_numpy().astype(np.float64)
    dates = [str(idx.date()) if hasattr(idx, "date") else str(idx) for idx in df.index]

    try:
        ind = compute_indicators(
            closes, high=highs, low=lows, volume=volumes, open_=opens
        )
    except Exception as exc:
        log.error("yfinance price_series: indicators failed for %s: %s", ticker, exc)
        ind = {}

    def _f(arr, i):
        if arr is None or len(arr) == 0:
            return None
        v = float(arr[i])
        return None if (v != v) else v

    start = 0 if window is None else max(0, len(closes) - window)
    series = [
        {
            "date": dates[i],
            "open": float(opens[i]),
            "high": float(highs[i]),
            "low": float(lows[i]),
            "close": float(closes[i]),
            "volume": float(volumes[i]),
            "sma20": _f(ind.get("sma20"), i),
            "ema9": _f(ind.get("ema9"), i),
            "ema20": _f(ind.get("ema20"), i),
            "ema50": _f(ind.get("ema50"), i),
            "vwap": _f(ind.get("vwap"), i),
            "bb_upper": _f(ind.get("bb_upper"), i),
            "bb_middle": _f(ind.get("bb_middle"), i),
            "bb_lower": _f(ind.get("bb_lower"), i),
            "macd_line": _f(ind.get("macd"), i),
            "macd_signal": _f(ind.get("macd_signal"), i),
            "macd_hist": _f(ind.get("macd_hist"), i),
            "rsi14": _f(ind.get("rsi14"), i),
            "atr14": _f(ind.get("atr14"), i),
            "stoch_k": _f(ind.get("stoch_k"), i),
            "stoch_d": _f(ind.get("stoch_d"), i),
            "obv": _f(ind.get("obv"), i),
        }
        for i in range(start, len(closes))
    ]

    def _last(key):
        return _f(ind.get(key), -1) if ind else None

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
    ticker = _normalize_idx_ticker(ticker)
    now = time.time()
    if (entry := _cache.get(ticker)) and now - entry.fetched_at < _CACHE_TTL:
        return entry.closes

    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        # Same still-open-session NaN as fetch_price_series_with_indicators.
        df = df[df["Close"].notna()]
    except Exception as exc:
        log.error("yfinance: fetch failed for %s: %s", ticker, exc)
        return np.array([])

    if df.empty:
        log.warning("yfinance: empty history for %s", ticker)
        return np.array([])

    closes = df["Close"].to_numpy()
    _cache[ticker] = _CacheEntry(closes=closes, fetched_at=now)
    return closes
