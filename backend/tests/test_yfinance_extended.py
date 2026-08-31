"""yfinance_client extended series tests."""
from __future__ import annotations

import numpy as np
import pytest

from app.agents.market import yfinance_client


def test_signature_keeps_positional_window():
    """Old call style (ticker, window=90) still works."""
    import inspect
    sig = inspect.signature(yfinance_client.fetch_price_series_with_indicators)
    params = list(sig.parameters)
    assert params[0] == "ticker"
    assert params[1] == "period"


def test_returns_ohlcv_keys_when_series_nonempty(monkeypatch):
    """With a real/mocked frame, series rows carry OHLCV + indicator keys."""
    import pandas as pd

    idx = pd.date_range("2024-01-01", periods=40, freq="D")
    n = len(idx)
    close = np.arange(1.0, n + 1.0)
    df = pd.DataFrame({
        "Open": close - 0.1,
        "High": close + 1.0,
        "Low": close - 1.0,
        "Close": close,
        "Volume": np.full(n, 1000.0),
    }, index=idx)

    # Monkeypatch yfinance history to return our deterministic frame.
    class FakeTicker:
        def history(self, **kwargs):
            return df.copy()

    monkeypatch.setattr(yfinance_client.yf, "Ticker", lambda t: FakeTicker())

    result = yfinance_client.fetch_price_series_with_indicators("BBCA", period="2mo", interval="1d", window=None)
    assert result["series"], "expected non-empty series"
    row = result["series"][-1]
    for key in ["date", "open", "high", "low", "close", "volume",
                "sma20", "ema9", "ema50", "vwap", "bb_upper", "macd_line",
                "rsi14", "atr14", "obv"]:
        assert key in row, f"missing key {key}"
    assert result["last_close"] == pytest.approx(float(close[-1]))


def test_window_limits_series_length(monkeypatch):
    import pandas as pd
    idx = pd.date_range("2024-01-01", periods=60, freq="D")
    n = len(idx)
    close = np.arange(1.0, n + 1.0)
    df = pd.DataFrame({
        "Open": close, "High": close + 1, "Low": close - 1,
        "Close": close, "Volume": np.full(n, 1000.0),
    }, index=idx)

    class FakeTicker:
        def history(self, **kwargs):
            return df.copy()

    monkeypatch.setattr(yfinance_client.yf, "Ticker", lambda t: FakeTicker())

    result = yfinance_client.fetch_price_series_with_indicators("BBCA", period="3mo", interval="1d", window=10)
    assert len(result["series"]) == 10