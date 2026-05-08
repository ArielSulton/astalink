import pytest

# Skip the whole file if TA-Lib isn't installed locally.
# In Docker (Dockerfile.dev), TA-Lib is built from source and installed.
pytest.importorskip("talib")

import numpy as np

from app.agents.market.indicators import compute_indicators


@pytest.fixture
def constant_close() -> np.ndarray:
    """30 days of price 100. SMA, EMA = 100 throughout. RSI undefined (no movement)."""
    return np.full(30, 100.0)


@pytest.fixture
def linear_uptrend() -> np.ndarray:
    """30 days, price increases by 1 each day from 100→129."""
    return np.arange(100, 130, dtype=np.float64)


def test_sma20_on_constant_series_equals_input_value(constant_close: np.ndarray) -> None:
    out = compute_indicators(close=constant_close)
    last_sma = out["sma20"][-1]
    assert last_sma == pytest.approx(100.0, abs=1e-6)


def test_rsi14_on_uptrend_is_high(linear_uptrend: np.ndarray) -> None:
    """A perfect uptrend has RSI close to 100."""
    out = compute_indicators(close=linear_uptrend)
    last_rsi = out["rsi14"][-1]
    assert last_rsi >= 90.0


def test_indicators_dict_has_expected_keys(linear_uptrend: np.ndarray) -> None:
    out = compute_indicators(close=linear_uptrend)
    assert set(out.keys()) >= {"sma20", "ema50", "rsi14", "macd", "bb_upper", "bb_lower"}


def test_short_series_returns_nan_indicators_without_crashing() -> None:
    """A 5-day series can't compute SMA20; indicator must be NaN at end, not crash."""
    short = np.array([100, 101, 102, 103, 104], dtype=np.float64)
    out = compute_indicators(close=short)
    assert np.isnan(out["sma20"][-1])
