"""A2 — Macro & Regulation (Indonesia / IDX).

Rule-based, numeric-only signals; no model calls. Three components:
- IHSG regime: last close vs SMA(trend_sma_days) + 3-month momentum
- FX regime: USDIDR momentum (rupiah weakening = risk-off for IDX)
- Fed regime: US 10Y Treasury yield (DGS10) momentum — rising US yields pull
  foreign capital out of EM markets like IDX (risk-off), unlike IHSG/FX this
  is a leading rather than a lagging read on the same domestic price action

Each component lands in [-1, 1]; the weighted mix maps to 0-100 with 50 as
neutral. Anything that can't be fetched stays None and is reported — a
missing macro read never silently becomes "neutral".
"""
from __future__ import annotations

import csv
import io
import logging
import time
from datetime import datetime, timezone

import httpx
import numpy as np
from pydantic import BaseModel, Field

from app.core.allocation_config import allocation_config

log = logging.getLogger(__name__)

_CACHE_TTL = 900
_cache: dict[str, tuple["MacroScore", float]] = {}

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


class MacroScore(BaseModel):
    score: float | None = None       # 0-100, None if nothing was fetchable
    ihsg_signal: float | None = None  # [-1, 1]
    fx_signal: float | None = None    # [-1, 1]
    fed_signal: float | None = None   # [-1, 1]
    detail: list[str] = Field(default_factory=list)
    as_of: str = ""


def _fetch_closes(symbol: str) -> np.ndarray:
    """Direct yfinance fetch. Deliberately NOT via yfinance_client's
    fetch_close_prices — that helper appends .JK to suffix-less symbols,
    which corrupts index (^JKSE) and FX (USDIDR=X) tickers."""
    import yfinance as yf
    try:
        df = yf.Ticker(symbol).history(period="1y", auto_adjust=True)
    except Exception as exc:
        log.error("macro: fetch failed for %s: %s", symbol, exc)
        return np.array([])
    return df["Close"].to_numpy() if not df.empty else np.array([])


def _fetch_fred_closes(series_id: str) -> np.ndarray:
    """FRED's public CSV export — free, official, no API key required
    (unlike the yfinance scrape used elsewhere in this module)."""
    try:
        resp = httpx.get(FRED_CSV_URL, params={"id": series_id}, timeout=10.0)
        resp.raise_for_status()
        rows = list(csv.reader(io.StringIO(resp.text)))
    except Exception as exc:
        log.error("macro: FRED fetch failed for %s: %s", series_id, exc)
        return np.array([])

    values: list[float] = []
    for row in rows[1:]:  # skip header (observation_date,<series_id>)
        if len(row) < 2 or row[1] in ("", "."):  # FRED uses "." for no-data days
            continue
        try:
            values.append(float(row[1]))
        except ValueError:
            continue
    return np.array(values)


def _momentum_signal(closes: np.ndarray, lookback: int, saturation: float) -> float | None:
    if len(closes) <= lookback or closes[-lookback] == 0:
        return None
    move = (closes[-1] - closes[-lookback]) / closes[-lookback]
    return float(np.clip(move / saturation, -1.0, 1.0))


def _absolute_change_signal(closes: np.ndarray, lookback: int, saturation_pts: float) -> float | None:
    """Like `_momentum_signal` but for series where an absolute-point move
    (e.g. a rate in percent) is meaningful and a relative-percent move is
    not (a rate near zero makes percent-change unstable/undefined)."""
    if len(closes) <= lookback:
        return None
    move = closes[-1] - closes[-lookback]
    return float(np.clip(move / saturation_pts, -1.0, 1.0))


def compute_macro_score(ihsg_closes: np.ndarray,
                        fx_closes: np.ndarray,
                        fed_closes: np.ndarray | None = None,
                        as_of: str = "") -> MacroScore:
    """Pure logic — testable without network. `fed_closes` is optional so
    existing two-signal callers keep working unchanged."""
    cfg = allocation_config.macro
    detail: list[str] = []

    ihsg_signal: float | None = None
    if len(ihsg_closes) >= cfg.trend_sma_days:
        sma = float(np.mean(ihsg_closes[-cfg.trend_sma_days:]))
        trend = 1.0 if ihsg_closes[-1] > sma else -1.0
        mom = _momentum_signal(ihsg_closes, cfg.momentum_lookback_days,
                               cfg.momentum_saturation_pct)
        parts = [trend] + ([mom] if mom is not None else [])
        ihsg_signal = float(np.mean(parts))
        detail.append(
            f"IHSG {'di atas' if trend > 0 else 'di bawah'} SMA{cfg.trend_sma_days}"
            + (f", momentum 3 bulan {mom:+.2f}" if mom is not None else ""))
    else:
        detail.append("Data IHSG tidak cukup untuk sinyal tren")

    fx_signal: float | None = None
    fx_mom = _momentum_signal(fx_closes, cfg.momentum_lookback_days,
                              cfg.momentum_saturation_pct)
    if fx_mom is not None:
        fx_signal = -fx_mom   # USDIDR rising = rupiah weakening = negative
        detail.append(f"USDIDR momentum 3 bulan {fx_mom:+.2f} "
                      f"({'rupiah melemah' if fx_mom > 0 else 'rupiah menguat'})")
    else:
        detail.append("Data USDIDR tidak cukup untuk sinyal FX")

    fed_signal: float | None = None
    if fed_closes is not None:
        fed_mom = _absolute_change_signal(fed_closes, cfg.momentum_lookback_days,
                                          cfg.fed_saturation_pts)
        if fed_mom is not None:
            fed_signal = -fed_mom   # rising US yield = capital flows out of EM = negative
            detail.append(f"US 10Y yield berubah {fed_mom:+.2f} poin dalam 3 bulan "
                          f"({'tekanan keluar dari EM' if fed_mom > 0 else 'kondusif bagi EM'})")
        else:
            detail.append("Data US 10Y yield tidak cukup untuk sinyal Fed")

    known = [(s, w) for s, w in ((ihsg_signal, cfg.ihsg_weight),
                                 (fx_signal, cfg.fx_weight),
                                 (fed_signal, cfg.fed_weight)) if s is not None]
    if not known:
        return MacroScore(score=None, detail=detail, as_of=as_of)
    total_w = sum(w for _, w in known)
    combined = sum(s * w for s, w in known) / total_w
    return MacroScore(score=50.0 + 50.0 * combined,
                      ihsg_signal=ihsg_signal, fx_signal=fx_signal,
                      fed_signal=fed_signal, detail=detail, as_of=as_of)


def fetch_macro_score() -> MacroScore:
    cfg = allocation_config.macro
    now = time.time()
    if (entry := _cache.get("macro")) and now - entry[1] < _CACHE_TTL:
        return entry[0]
    score = compute_macro_score(
        _fetch_closes(cfg.ihsg_symbol),
        _fetch_closes(cfg.fx_symbol),
        _fetch_fred_closes(cfg.fed_symbol),
        as_of=datetime.now(timezone.utc).isoformat(),
    )
    _cache["macro"] = (score, now)
    return score
