"""Hybrid stock recommendations: cosine similarity, sector vectors,
content score, user score, cold-start fallback, hybrid combine, and the
GET /api/v1/recommendations endpoint."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from app.core.recommendations import (
    _bare_ticker,
    _cosine_similarity,
    _normalize_to_100,
    _sector_vectors_by_workspace,
    build_recommendations,
    user_scores,
)
from app.models.recommendations import RecommendationsResponse


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


def test_build_recommendations_ranks_eligible_by_hybrid_score_and_caps_verdicts():
    content_by_ticker = {"BBCA": 80.0, "TLKM": 60.0, "ASII": 40.0}
    user_by_ticker = {"BBCA": 40.0, "TLKM": 80.0, "ASII": 0.0}
    # normalized user: BBCA=50, TLKM=100, ASII=0
    # hybrid: BBCA=65, TLKM=80, ASII=20 -> ranked TLKM, BBCA, ASII

    fake_engine_result = {
        "verdicts": {
            "BBCA": {"ticker": "BBCA", "band": "buy", "score": 75.0, "horizon": "3-6 bulan",
                      "invalidation_condition": "—", "components": {}, "gate_status": "pass",
                      "manipulation_risk": "low", "evidence_gaps": [], "detail": [],
                      "as_of": "2026-09-01T00:00:00+00:00"},
            "TLKM": {"ticker": "TLKM", "band": "buy", "score": 70.0, "horizon": "3-6 bulan",
                      "invalidation_condition": "—", "components": {}, "gate_status": "pass",
                      "manipulation_risk": "low", "evidence_gaps": [], "detail": [],
                      "as_of": "2026-09-01T00:00:00+00:00"},
            "ASII": {"ticker": "ASII", "band": "watchlist", "score": 55.0, "horizon": "3-6 bulan",
                      "invalidation_condition": "—", "components": {}, "gate_status": "pass",
                      "manipulation_risk": "low", "evidence_gaps": [], "detail": [],
                      "as_of": "2026-09-01T00:00:00+00:00"},
        },
        "eligible_tickers": ["BBCA", "TLKM", "ASII"],
        "macro": {"score": 50.0, "detail": [], "as_of": "2026-09-01T00:00:00+00:00"},
        "as_of": "2026-09-01T00:00:00+00:00",
    }

    with patch("app.core.recommendations.TICKER_SECTOR", {"BBCA": "banking", "TLKM": "telco", "ASII": "industrials"}), \
         patch("app.core.recommendations.content_score_for", side_effect=lambda t: content_by_ticker.get(t)), \
         patch("app.core.recommendations.user_scores", return_value=(user_by_ticker, True, None)), \
         patch("app.core.recommendations.fetch_news", return_value=[]), \
         patch("app.core.recommendations.run_stock_engine", return_value=fake_engine_result) as mock_engine, \
         patch("app.core.recommendations._TOP_N_ENRICHED", 2):
        result = build_recommendations(MagicMock(), "ws-1")

    assert [item.ticker for item in result.items] == ["TLKM", "BBCA", "ASII"]
    assert result.items[0].hybrid_score == 80.0
    assert result.items[0].rank == 1
    assert result.personalized is True
    assert result.workspace_id == "ws-1"

    # _TOP_N_ENRICHED patched to 2: only the top 2 (TLKM, BBCA) keep their verdict;
    # ASII (rank 3, still eligible) has verdict=None despite being enriched internally.
    assert result.items[0].verdict is not None and result.items[0].verdict.band == "buy"
    assert result.items[1].verdict is not None
    assert result.items[2].verdict is None

    # run_stock_engine is now called with the FULL viable set, before ranking/filtering
    # (needed to determine eligible_tickers up front), not just the ranked top-N.
    mock_engine.assert_called_once()
    called_tickers = mock_engine.call_args.args[0]
    assert called_tickers == ["BBCA", "TLKM", "ASII"]


def test_build_recommendations_excludes_ineligible_tickers_entirely():
    """A ticker whose verdict band is REJECT (fails the engine's own
    eligible_tickers gate) must not appear anywhere in the ranked results
    — not just lack a verdict, but be excluded from ranking entirely. This
    is the compliance-driven behavior: a REJECT-band stock must never be
    shown on a "worth buying" page regardless of its technical/CF score,
    even if that score would otherwise rank it #1."""
    content_by_ticker = {"BBCA": 80.0, "TLKM": 90.0, "ASII": 40.0}
    # TLKM scores highest on content, but the engine rejects it.

    fake_engine_result = {
        "verdicts": {
            "BBCA": {"ticker": "BBCA", "band": "buy", "score": 75.0, "horizon": "3-6 bulan",
                      "invalidation_condition": "—", "components": {}, "gate_status": "pass",
                      "manipulation_risk": "low", "evidence_gaps": [], "detail": [],
                      "as_of": "2026-09-01T00:00:00+00:00"},
            "TLKM": {"ticker": "TLKM", "band": "reject", "score": None, "horizon": "3-6 bulan",
                      "invalidation_condition": "—", "components": {}, "gate_status": "fail",
                      "manipulation_risk": "high", "evidence_gaps": [], "detail": [],
                      "as_of": "2026-09-01T00:00:00+00:00"},
            "ASII": {"ticker": "ASII", "band": "watchlist", "score": 55.0, "horizon": "3-6 bulan",
                      "invalidation_condition": "—", "components": {}, "gate_status": "pass",
                      "manipulation_risk": "low", "evidence_gaps": [], "detail": [],
                      "as_of": "2026-09-01T00:00:00+00:00"},
        },
        "eligible_tickers": ["BBCA", "ASII"],  # TLKM excluded — REJECT band
        "macro": {"score": 50.0, "detail": [], "as_of": "2026-09-01T00:00:00+00:00"},
        "as_of": "2026-09-01T00:00:00+00:00",
    }

    with patch("app.core.recommendations.TICKER_SECTOR", {"BBCA": "banking", "TLKM": "telco", "ASII": "industrials"}), \
         patch("app.core.recommendations.content_score_for", side_effect=lambda t: content_by_ticker.get(t)), \
         patch("app.core.recommendations.user_scores", return_value=({}, False, "cold start")), \
         patch("app.core.recommendations.fetch_news", return_value=[]), \
         patch("app.core.recommendations.run_stock_engine", return_value=fake_engine_result):
        result = build_recommendations(MagicMock(), "ws-1")

    tickers_in_result = [item.ticker for item in result.items]
    assert "TLKM" not in tickers_in_result, "REJECT-band ticker must be excluded from ranking entirely"
    assert tickers_in_result == ["BBCA", "ASII"]  # BBCA ranks first: content 80 > ASII's 40


def test_build_recommendations_cold_start_uses_content_score_only():
    content_by_ticker = {"BBCA": 80.0}
    fake_engine_result = {
        "verdicts": {
            "BBCA": {"ticker": "BBCA", "band": "buy", "score": 80.0, "horizon": "3-6 bulan",
                      "invalidation_condition": "—", "components": {}, "gate_status": "pass",
                      "manipulation_risk": "low", "evidence_gaps": [], "detail": [],
                      "as_of": "2026-09-01T00:00:00+00:00"},
        },
        "eligible_tickers": ["BBCA"],
        "macro": {"score": None, "detail": [], "as_of": ""},
        "as_of": "",
    }

    with patch("app.core.recommendations.TICKER_SECTOR", {"BBCA": "banking"}), \
         patch("app.core.recommendations.content_score_for", side_effect=lambda t: content_by_ticker.get(t)), \
         patch("app.core.recommendations.user_scores", return_value=({}, False, "belum ada histori")), \
         patch("app.core.recommendations.fetch_news", return_value=[]), \
         patch("app.core.recommendations.run_stock_engine", return_value=fake_engine_result):
        result = build_recommendations(MagicMock(), "ws-1")

    assert result.personalized is False
    assert result.fallback_reason == "belum ada histori"
    assert result.items[0].hybrid_score == 80.0   # content-only, not 0.5*80


def test_normalize_to_100_rescales_min_max():
    scores = {"BBCA": 40.0, "TLKM": 80.0, "ASII": 0.0}
    normalized = _normalize_to_100(scores)
    assert normalized["ASII"] == 0.0
    assert normalized["TLKM"] == 100.0
    assert normalized["BBCA"] == 50.0


def test_normalize_to_100_all_equal_nonzero_maps_to_fifty():
    scores = {"BBCA": 25.0, "TLKM": 25.0, "ASII": 25.0}
    normalized = _normalize_to_100(scores)
    assert normalized == {"BBCA": 50.0, "TLKM": 50.0, "ASII": 50.0}


def test_normalize_to_100_all_zero_maps_to_zero():
    scores = {"BBCA": 0.0, "TLKM": 0.0}
    normalized = _normalize_to_100(scores)
    assert normalized == {"BBCA": 0.0, "TLKM": 0.0}


def test_normalize_to_100_empty_dict_returns_empty():
    assert _normalize_to_100({}) == {}


def test_build_recommendations_verdict_enrichment_failure_degrades_gracefully():
    """If run_stock_engine raises, eligibility can't be determined for any
    candidate at all, so this fails closed: zero recommendations rather
    than falling back to an unfiltered (and therefore unvetted) list."""
    content_by_ticker = {"BBCA": 80.0, "TLKM": 60.0}

    with patch("app.core.recommendations.TICKER_SECTOR", {"BBCA": "banking", "TLKM": "telco"}), \
         patch("app.core.recommendations.content_score_for", side_effect=lambda t: content_by_ticker.get(t)), \
         patch("app.core.recommendations.user_scores", return_value=({}, False, "belum ada histori")), \
         patch("app.core.recommendations.fetch_news", return_value=[]), \
         patch("app.core.recommendations.run_stock_engine", side_effect=RuntimeError("boom")):
        result = build_recommendations(MagicMock(), "ws-1")

    assert isinstance(result, RecommendationsResponse)
    assert result.items == []


def test_recommendations_route_registered():
    from app.api.v1 import recommendations as recommendations_module
    seen = {r.path for r in recommendations_module.router.routes}
    assert "" in seen


def test_recommendations_requires_ownership(client) -> None:
    mock_user = {"sub": str(uuid.uuid4())}
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.recommendations.get_admin_client", return_value=fake_admin):
        resp = client.get(
            "/api/v1/recommendations?workspace_id=not-mine",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 403


def test_recommendations_returns_build_result(client) -> None:
    mock_user = {"sub": str(uuid.uuid4())}
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": "ws-1"}])

    fake_response = RecommendationsResponse(
        workspace_id="ws-1", personalized=False,
        fallback_reason="belum ada histori", items=[],
        as_of="2026-09-01T00:00:00+00:00",
    )

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.recommendations.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.recommendations.build_recommendations", return_value=fake_response):
        resp = client.get(
            "/api/v1/recommendations?workspace_id=ws-1",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["personalized"] is False
    assert body["workspace_id"] == "ws-1"
    assert body["items"] == []
