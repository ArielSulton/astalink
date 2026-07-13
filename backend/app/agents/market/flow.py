"""A4 — Smart Money / Flow.

True foreign-flow (net asing) and broker-summary data are NOT available
from the free data source — that limitation is declared in `evidence_gaps`,
never papered over. What CAN be computed from OHLCV:

- OBV (on-balance volume) trend: is volume backing the price direction?
- Accumulation/Distribution line trend: are closes landing near highs
  (accumulation) or lows (distribution)?
- Volume-weighted up/down ratio over the window.

Each component lands in [-1, 1]; equal-weight mix maps to 0-100.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import numpy as np
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

_CACHE_TTL = 300
_cache: dict[str, tuple["FlowScore", float]] = {}

EVIDENCE_GAPS = [
    "Data net beli/jual asing (foreign flow) tidak tersedia dari sumber data",
    "Broker summary tidak tersedia — proxy volume dipakai sebagai gantinya",
]


class FlowScore(BaseModel):
    score: float | None = None      # 0-100; None when data insufficient
    obv_signal: float | None = None
    ad_signal: float | None = None
    volume_ratio_signal: float | None = None
    evidence_gaps: list[str] = Field(default_factory=lambda: list(EVIDENCE_GAPS))
    detail: list[str] = Field(default_factory=list)
    as_of: str = ""


def _trend_signal(series: np.ndarray, window: int = 20) -> float | None:
    """Sign+strength of the linear trend of the last `window` points,
    normalized by the series' scale. Clipped to [-1, 1]."""
    if len(series) < window:
        return None
    tail = series[-window:]
    scale = float(np.std(tail))
    if scale == 0:
        return 0.0
    slope = float(np.polyfit(np.arange(window), tail, 1)[0])
    return float(np.clip(slope * window / (4 * scale), -1.0, 1.0))


def compute_flow_score(highs: np.ndarray, lows: np.ndarray,
                       closes: np.ndarray, volumes: np.ndarray,
                       as_of: str = "") -> FlowScore:
    """Pure logic — testable without network."""
    detail: list[str] = []
    n = min(len(highs), len(lows), len(closes), len(volumes))
    if n < 21:
        return FlowScore(score=None, as_of=as_of,
                         detail=["Data OHLCV tidak cukup (< 21 hari)"])
    highs, lows, closes, volumes = highs[-n:], lows[-n:], closes[-n:], volumes[-n:]

    # OBV
    direction = np.sign(np.diff(closes))
    obv = np.concatenate([[0.0], np.cumsum(direction * volumes[1:])])
    obv_signal = _trend_signal(obv)
    if obv_signal is not None:
        detail.append(f"Tren OBV {obv_signal:+.2f}")

    # Accumulation/Distribution line
    rng = highs - lows
    with np.errstate(divide="ignore", invalid="ignore"):
        clv = np.where(rng > 0, ((closes - lows) - (highs - closes)) / rng, 0.0)
    ad = np.cumsum(clv * volumes)
    ad_signal = _trend_signal(ad)
    if ad_signal is not None:
        detail.append(f"Tren garis A/D {ad_signal:+.2f}")

    # Volume-weighted up/down ratio (last 20 sessions)
    up_vol = float(np.sum(volumes[1:][direction > 0][-20:]))
    down_vol = float(np.sum(volumes[1:][direction < 0][-20:]))
    vol_signal = None
    if up_vol + down_vol > 0:
        vol_signal = (up_vol - down_vol) / (up_vol + down_vol)
        detail.append(f"Rasio volume naik/turun {vol_signal:+.2f}")

    known = [s for s in (obv_signal, ad_signal, vol_signal) if s is not None]
    if not known:
        return FlowScore(score=None, detail=detail, as_of=as_of)
    combined = float(np.mean(known))
    return FlowScore(score=50.0 + 50.0 * combined, obv_signal=obv_signal,
                     ad_signal=ad_signal, volume_ratio_signal=vol_signal,
                     detail=detail, as_of=as_of)


def fetch_flow_score(ticker: str) -> FlowScore:
    import yfinance as yf

    from app.agents.market.yfinance_client import _normalize_idx_ticker

    yf_ticker = _normalize_idx_ticker(ticker)
    now = time.time()
    if (entry := _cache.get(yf_ticker)) and now - entry[1] < _CACHE_TTL:
        return entry[0]
    try:
        df = yf.Ticker(yf_ticker).history(period="6mo", auto_adjust=True)
    except Exception as exc:
        log.error("flow: fetch failed for %s: %s", ticker, exc)
        df = None
    if df is None or df.empty:
        score = FlowScore(score=None, detail=["Data harga tidak tersedia"],
                          as_of=datetime.now(timezone.utc).isoformat())
    else:
        score = compute_flow_score(
            df["High"].to_numpy(), df["Low"].to_numpy(),
            df["Close"].to_numpy(), df["Volume"].to_numpy(),
            as_of=datetime.now(timezone.utc).isoformat(),
        )
    _cache[yf_ticker] = (score, now)
    return score
