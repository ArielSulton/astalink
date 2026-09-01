"""Watchlist/chart endpoint tests (mocked yfinance)."""
from __future__ import annotations

import pytest

from app.api.v1 import market as market_module


def test_build_chart_data_returns_series(monkeypatch):
    monkeypatch.setattr(market_module, "fetch_price_series_with_indicators", lambda t, period, interval: {
        "series": [{"date": "2024-01-01", "close": 100.0}],
        "last_close": 100.0, "prev_close": 99.0,
        "rsi14": None, "sma20": None, "macd": None, "bb_upper": None, "bb_lower": None,
    })
    out = market_module._build_chart_data("BBCA.JK", "1mo", "1d")
    assert out.ticker == "BBCA.JK"
    assert out.price_change_pct == pytest.approx((100 - 99) / 99 * 100)
    assert len(out.price_series) == 1
    assert out.price_series[0].date == "2024-01-01"
    assert out.price_series[0].close == 100.0


def test_build_chart_data_handles_none_values(monkeypatch):
    """Test that _build_chart_data handles None values gracefully."""
    monkeypatch.setattr(market_module, "fetch_price_series_with_indicators", lambda t, period, interval: {
        "series": [{"date": "2024-01-01", "close": 100.0}],
        "last_close": None, "prev_close": None,
        "rsi14": None, "sma20": None, "macd": None, "bb_upper": None, "bb_lower": None,
    })
    out = market_module._build_chart_data("BBCA.JK", "1mo", "1d")
    assert out.ticker == "BBCA.JK"
    assert out.last_close is None
    assert out.prev_close is None
    assert out.price_change_pct is None


def test_build_chart_data_with_full_series(monkeypatch):
    """Test _build_chart_data with a full series including all indicator fields."""
    full_series = [
        {
            "date": "2024-01-01",
            "open": 99.0, "high": 101.0, "low": 98.0, "close": 100.0, "volume": 1000.0,
            "sma20": 99.5, "ema9": 99.8, "ema20": 99.6, "ema50": 99.2,
            "vwap": 99.9, "bb_upper": 102.0, "bb_middle": 100.0, "bb_lower": 98.0,
            "macd_line": 0.5, "macd_signal": 0.3, "macd_hist": 0.2,
            "rsi14": 55.0, "atr14": 1.5, "stoch_k": 60.0, "stoch_d": 58.0, "obv": 5000.0,
        },
        {
            "date": "2024-01-02",
            "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1100.0,
            "sma20": 100.0, "ema9": 100.5, "ema20": 100.2, "ema50": 99.8,
            "vwap": 100.8, "bb_upper": 103.0, "bb_middle": 101.0, "bb_lower": 99.0,
            "macd_line": 0.6, "macd_signal": 0.4, "macd_hist": 0.2,
            "rsi14": 58.0, "atr14": 1.6, "stoch_k": 65.0, "stoch_d": 62.0, "obv": 5100.0,
        },
    ]
    monkeypatch.setattr(market_module, "fetch_price_series_with_indicators", lambda t, period, interval: {
        "series": full_series,
        "last_close": 101.0, "prev_close": 100.0,
        "rsi14": 58.0, "sma20": 100.0, "macd": 0.6, "bb_upper": 103.0, "bb_lower": 99.0,
    })
    out = market_module._build_chart_data("BBCA.JK", "1mo", "1d")
    assert out.ticker == "BBCA.JK"
    assert out.last_close == 101.0
    assert out.prev_close == 100.0
    assert out.price_change_pct == pytest.approx(1.0)
    assert out.rsi14 == 58.0
    assert out.sma20 == 100.0
    assert out.macd == 0.6
    assert out.bb_upper == 103.0
    assert out.bb_lower == 99.0
    assert len(out.price_series) == 2
    # Verify all PricePoint fields are populated
    pp = out.price_series[0]
    assert pp.date == "2024-01-01"
    assert pp.open == 99.0
    assert pp.high == 101.0
    assert pp.low == 98.0
    assert pp.close == 100.0
    assert pp.volume == 1000.0
    assert pp.sma20 == 99.5
    assert pp.ema9 == 99.8
    assert pp.ema20 == 99.6
    assert pp.ema50 == 99.2
    assert pp.vwap == 99.9
    assert pp.bb_upper == 102.0
    assert pp.bb_middle == 100.0
    assert pp.bb_lower == 98.0
    assert pp.macd_line == 0.5
    assert pp.macd_signal == 0.3
    assert pp.macd_hist == 0.2
    assert pp.rsi14 == 55.0
    assert pp.atr14 == 1.5
    assert pp.stoch_k == 60.0
    assert pp.stoch_d == 58.0
    assert pp.obv == 5000.0