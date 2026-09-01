"""Hybrid stock recommendations: cosine similarity, sector vectors,
content score, user score, cold-start fallback, hybrid combine, and the
GET /api/v1/recommendations endpoint."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from app.core.recommendations import (
    _bare_ticker,
    _cosine_similarity,
    _sector_vectors_by_workspace,
)


def test_bare_ticker_strips_exchange_suffix():
    assert _bare_ticker("BBCA.JK") == "BBCA"
    assert _bare_ticker("bbca") == "BBCA"


def test_cosine_similarity_identical_vectors_is_one():
    v = {"banking": 0.6, "telco": 0.4}
    assert abs(_cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal_vectors_is_zero():
    a = {"banking": 1.0}
    b = {"telco": 1.0}
    assert _cosine_similarity(a, b) == 0.0


def test_cosine_similarity_empty_vector_is_zero():
    assert _cosine_similarity({}, {"banking": 1.0}) == 0.0


def test_sector_vectors_by_workspace_normalizes_and_groups():
    rows = [
        # ws-1: 100% banking (BBCA.JK, cost basis 10*1000)
        {"workspace_id": "ws-1", "ticker": "BBCA.JK", "quantity": 10, "avg_cost": 1000},
        # ws-2: half banking (BMRI), half telco (TLKM)
        {"workspace_id": "ws-2", "ticker": "BMRI.JK", "quantity": 5, "avg_cost": 1000},
        {"workspace_id": "ws-2", "ticker": "TLKM.JK", "quantity": 5, "avg_cost": 1000},
    ]
    fake_sb = MagicMock()
    fake_sb.table.return_value.select.return_value.execute.return_value = MagicMock(data=rows)

    vectors = _sector_vectors_by_workspace(fake_sb)

    assert vectors["ws-1"] == {"banking": 1.0}
    assert abs(vectors["ws-2"]["banking"] - 0.5) < 1e-9
    assert abs(vectors["ws-2"]["telco"] - 0.5) < 1e-9


def test_rsi_zone_score_healthy_band_is_max():
    from app.core.recommendations import _rsi_zone_score
    assert _rsi_zone_score(55.0) == 1.0
    assert _rsi_zone_score(45.0) == 1.0
    assert _rsi_zone_score(70.0) == 1.0


def test_rsi_zone_score_tapers_toward_extremes():
    from app.core.recommendations import _rsi_zone_score
    assert abs(_rsi_zone_score(32.5) - 0.5) < 1e-9   # midpoint of 20-45 taper
    assert abs(_rsi_zone_score(77.5) - 0.5) < 1e-9   # midpoint of 70-85 taper


def test_rsi_zone_score_extreme_is_zero():
    from app.core.recommendations import _rsi_zone_score
    assert _rsi_zone_score(10.0) == 0.0
    assert _rsi_zone_score(95.0) == 0.0


def test_content_score_all_bullish_checks_scores_100():
    from app.core.recommendations import content_score_for
    data = {"last_close": 110.0, "sma20": 100.0, "rsi14": 55.0, "macd": 1.5, "bb_upper": 120.0}
    with patch("app.core.recommendations.fetch_price_series_with_indicators", return_value=data):
        assert content_score_for("BBCA") == 100.0


def test_content_score_all_bearish_checks_scores_0():
    from app.core.recommendations import content_score_for
    data = {"last_close": 90.0, "sma20": 100.0, "rsi14": 90.0, "macd": -1.5, "bb_upper": 85.0}
    with patch("app.core.recommendations.fetch_price_series_with_indicators", return_value=data):
        assert content_score_for("BBCA") == 0.0


def test_content_score_excludes_missing_fields_and_renormalizes():
    from app.core.recommendations import content_score_for
    # Only rsi14 known (healthy zone -> full marks); everything else missing.
    data = {"last_close": None, "sma20": None, "rsi14": 60.0, "macd": None, "bb_upper": None}
    with patch("app.core.recommendations.fetch_price_series_with_indicators", return_value=data):
        assert content_score_for("BBCA") == 100.0


def test_content_score_returns_none_when_all_fields_missing():
    from app.core.recommendations import content_score_for
    data = {"last_close": None, "sma20": None, "rsi14": None, "macd": None, "bb_upper": None}
    with patch("app.core.recommendations.fetch_price_series_with_indicators", return_value=data):
        assert content_score_for("BBCA") is None
