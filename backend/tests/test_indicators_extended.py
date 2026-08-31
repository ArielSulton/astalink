"""Extended indicator pack tests."""
from __future__ import annotations

import numpy as np
import pytest

from app.agents.market.indicators import compute_indicators


def _flat(n: int, base: float = 100.0) -> np.ndarray:
    return np.full(n, base, dtype=np.float64)


def test_vwap_requires_volume():
    """VWAP needs volume + high/low/open; without them it's all-NaN."""
    close = _flat(30)
    out = compute_indicators(close)  # no volume/high/low passed
    assert "vwap" in out
    assert np.isnan(out["vwap"]).all()


def test_atr_requires_high_low():
    """ATR without high/low is all-NaN."""
    out = compute_indicators(_flat(30))
    assert "atr14" in out
    assert np.isnan(out["atr14"]).all()


def test_ema9_computed():
    s = np.arange(1.0, 101.0)  # linearly rising
    out = compute_indicators(s)
    ema9 = out["ema9"]
    assert not np.isnan(ema9[-1])
    # On a rising series, EMA9 starts null then converges upward.
    assert np.isnan(ema9[:8]).all()
    assert ema9[-1] > 90


def test_macd_hist_present():
    out = compute_indicators(np.arange(1.0, 101.0))
    assert not np.isnan(out["macd_hist"][-1])


def test_empty_input():
    out = compute_indicators(np.array([]))
    for v in out.values():
        assert isinstance(v, np.ndarray)
        assert v.size == 0