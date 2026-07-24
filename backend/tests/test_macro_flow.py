"""A2 macro + A4 flow (pure logic, no network)."""
from __future__ import annotations

import numpy as np

from app.agents.market.flow import compute_flow_score
from app.agents.market.macro import compute_macro_score


# --- A2 macro ---

def test_bullish_ihsg_strong_rupiah_scores_above_neutral():
    ihsg = np.linspace(6000, 7500, 250)      # steady uptrend
    fx = np.linspace(16500, 15500, 250)      # rupiah strengthening
    res = compute_macro_score(ihsg, fx)
    assert res.score is not None and res.score > 60
    assert res.ihsg_signal is not None and res.ihsg_signal > 0
    assert res.fx_signal is not None and res.fx_signal > 0


def test_bearish_ihsg_weak_rupiah_scores_below_neutral():
    ihsg = np.linspace(7500, 6000, 250)
    fx = np.linspace(15500, 17000, 250)
    res = compute_macro_score(ihsg, fx)
    assert res.score is not None and res.score < 40


def test_insufficient_data_is_none_not_neutral():
    res = compute_macro_score(np.array([1.0, 2.0]), np.array([]))
    assert res.score is None
    assert any("tidak cukup" in d for d in res.detail)


# --- A4 flow ---

def _ohlcv(closes: np.ndarray, volumes: np.ndarray):
    highs = closes * 1.01
    lows = closes * 0.99
    return highs, lows, closes, volumes


def test_accumulation_pattern_scores_above_neutral():
    closes = np.linspace(100, 130, 60)
    volumes = np.linspace(1e6, 3e6, 60)      # rising volume with rising price
    res = compute_flow_score(*_ohlcv(closes, volumes))
    assert res.score is not None and res.score > 55


def test_distribution_pattern_scores_below_neutral():
    closes = np.linspace(130, 100, 60)
    volumes = np.linspace(1e6, 3e6, 60)
    res = compute_flow_score(*_ohlcv(closes, volumes))
    assert res.score is not None and res.score < 45


def test_short_series_returns_none():
    closes = np.linspace(100, 101, 10)
    res = compute_flow_score(*_ohlcv(closes, np.ones(10)))
    assert res.score is None


def test_foreign_flow_evidence_gap_always_declared():
    closes = np.linspace(100, 130, 60)
    res = compute_flow_score(*_ohlcv(closes, np.ones(60) * 1e6))
    assert any("foreign flow" in g for g in res.evidence_gaps)
