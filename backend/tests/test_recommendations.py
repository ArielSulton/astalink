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
    build_recommendations,
    user_scores,
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


def test_user_scores_cold_start_when_workspace_has_no_holdings():
    fake_sb = MagicMock()
    fake_sb.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])

    scores, personalized, reason = user_scores(fake_sb, "ws-empty", ["BBCA"])

    assert scores == {}
    assert personalized is False
    assert reason is not None


def test_user_scores_cold_start_when_too_few_comparable_workspaces():
    rows = [
        {"workspace_id": "ws-me", "ticker": "BBCA.JK", "quantity": 10, "avg_cost": 1000},
        {"workspace_id": "ws-other", "ticker": "BMRI.JK", "quantity": 10, "avg_cost": 1000},
    ]
    fake_sb = MagicMock()
    fake_sb.table.return_value.select.return_value.execute.return_value = MagicMock(data=rows)

    scores, personalized, reason = user_scores(fake_sb, "ws-me", ["BBCA"])

    assert scores == {}
    assert personalized is False
    assert reason is not None


def test_user_scores_personalizes_with_enough_similar_workspaces():
    rows = [
        {"workspace_id": "ws-me", "ticker": "BBCA.JK", "quantity": 10, "avg_cost": 1000},
    ]
    # Three "similar" workspaces, all banking-heavy like ws-me.
    for i in range(3):
        rows.append({
            "workspace_id": f"ws-sim-{i}", "ticker": "BMRI.JK",
            "quantity": 10, "avg_cost": 1000,
        })
    fake_sb = MagicMock()
    fake_sb.table.return_value.select.return_value.execute.return_value = MagicMock(data=rows)

    scores, personalized, reason = user_scores(fake_sb, "ws-me", ["BBCA", "TLKM"])

    assert personalized is True
    assert reason is None
    assert scores["BBCA"] == 100.0   # all comparable workspaces are 100% banking
    assert scores["TLKM"] == 0.0     # no comparable workspace holds telco


def test_build_recommendations_ranks_by_hybrid_score_and_enriches_top_n():
    content_by_ticker = {"BBCA": 80.0, "TLKM": 60.0, "ASII": 40.0}
    user_by_ticker = {"BBCA": 40.0, "TLKM": 80.0, "ASII": 0.0}
    # hybrid: BBCA=60, TLKM=70, ASII=20 -> ranked TLKM, BBCA, ASII

    fake_engine_result = {
        "verdicts": {
            "TLKM": {
                "ticker": "TLKM", "band": "buy", "score": 70.0, "horizon": "3-6 bulan",
                "invalidation_condition": "—", "components": {}, "gate_status": "pass",
                "manipulation_risk": "low", "evidence_gaps": [], "detail": [],
                "as_of": "2026-09-01T00:00:00+00:00",
            },
            # BBCA/ASII intentionally absent: run_stock_engine already drops
            # per-ticker failures from its verdicts dict internally.
        },
        "eligible_tickers": ["TLKM"],
        "macro": {"score": 50.0, "detail": [], "as_of": "2026-09-01T00:00:00+00:00"},
        "as_of": "2026-09-01T00:00:00+00:00",
    }

    with patch("app.core.recommendations.TICKER_SECTOR", {"BBCA": "banking", "TLKM": "telco", "ASII": "industrials"}), \
         patch("app.core.recommendations.content_score_for", side_effect=lambda t: content_by_ticker.get(t)), \
         patch("app.core.recommendations.user_scores", return_value=(user_by_ticker, True, None)), \
         patch("app.core.recommendations.fetch_news", return_value=[]), \
         patch("app.core.recommendations.run_stock_engine", return_value=fake_engine_result) as mock_engine:
        result = build_recommendations(MagicMock(), "ws-1")

    assert [item.ticker for item in result.items] == ["TLKM", "BBCA", "ASII"]
    assert result.items[0].hybrid_score == 70.0
    assert result.items[0].rank == 1
    assert result.items[0].verdict is not None
    assert result.items[0].verdict.band == "buy"
    assert result.items[1].verdict is None
    assert result.items[2].verdict is None
    assert result.personalized is True
    assert result.workspace_id == "ws-1"

    # All 3 candidates fit under the top-8 enrichment cap, so run_stock_engine
    # must have been called once with every one of them (order = ranked order).
    mock_engine.assert_called_once()
    called_tickers = mock_engine.call_args.args[0]
    assert called_tickers == ["TLKM", "BBCA", "ASII"]


def test_build_recommendations_cold_start_uses_content_score_only():
    content_by_ticker = {"BBCA": 80.0}

    with patch("app.core.recommendations.TICKER_SECTOR", {"BBCA": "banking"}), \
         patch("app.core.recommendations.content_score_for", side_effect=lambda t: content_by_ticker.get(t)), \
         patch("app.core.recommendations.user_scores", return_value=({}, False, "belum ada histori")), \
         patch("app.core.recommendations.fetch_news", return_value=[]), \
         patch("app.core.recommendations.run_stock_engine", return_value={"verdicts": {}, "eligible_tickers": [], "macro": {"score": None, "detail": [], "as_of": ""}, "as_of": ""}):
        result = build_recommendations(MagicMock(), "ws-1")

    assert result.personalized is False
    assert result.fallback_reason == "belum ada histori"
    assert result.items[0].hybrid_score == 80.0   # content-only, not 0.5*80
