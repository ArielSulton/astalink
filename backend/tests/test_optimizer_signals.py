"""Unit tests for the optimizer's real-signal inputs (μ tilt + covariance)."""
from app.agents.optimizer.node import (
    _DEFAULT_EXPECTED_RETURN,
    _DEFAULT_VARIANCE,
    _SCORE_TILT,
    _covariance,
    _expected_returns,
)


def test_expected_returns_falls_back_to_flat_prior_without_data() -> None:
    er = _expected_returns(["BBCA", "TLKM"], ents={})
    assert er == [_DEFAULT_EXPECTED_RETURN, _DEFAULT_EXPECTED_RETURN]


def test_expected_returns_uses_historical_mu() -> None:
    ents = {"risk_metrics": {"expected_returns": {"BBCA": 0.15, "TLKM": 0.05}}}
    assert _expected_returns(["BBCA", "TLKM"], ents) == [0.15, 0.05]


def test_expected_returns_tilts_by_verdict_score() -> None:
    ents = {
        "risk_metrics": {"expected_returns": {"BBCA": 0.10, "TLKM": 0.10}},
        "stock_engine": {"verdicts": {
            "BBCA": {"score": 100},   # max bullish → +tilt
            "TLKM": {"score": 0},     # max bearish → −tilt
        }},
    }
    er = _expected_returns(["BBCA", "TLKM"], ents)
    assert er[0] == 0.10 + _SCORE_TILT
    assert er[1] == 0.10 - _SCORE_TILT
    assert er[0] > er[1]


def test_expected_returns_neutral_score_no_tilt() -> None:
    ents = {
        "risk_metrics": {"expected_returns": {"BBCA": 0.10}},
        "stock_engine": {"verdicts": {"BBCA": {"score": 50}}},
    }
    assert _expected_returns(["BBCA"], ents) == [0.10]


def test_expected_returns_handles_null_score() -> None:
    ents = {
        "risk_metrics": {"expected_returns": {"BBCA": 0.12}},
        "stock_engine": {"verdicts": {"BBCA": {"score": None}}},
    }
    assert _expected_returns(["BBCA"], ents) == [0.12]


def test_covariance_falls_back_to_diagonal_without_data() -> None:
    cov = _covariance(["BBCA", "TLKM"], ents={})
    assert cov == [[_DEFAULT_VARIANCE, 0.0], [0.0, _DEFAULT_VARIANCE]]


def test_covariance_subsets_risk_matrix_in_ticker_order() -> None:
    ents = {"risk_metrics": {"covariance": {
        "BBCA": {"BBCA": 0.04, "TLKM": 0.01},
        "TLKM": {"BBCA": 0.01, "TLKM": 0.09},
    }}}
    cov = _covariance(["TLKM", "BBCA"], ents)   # reversed order
    assert cov == [[0.09, 0.01], [0.01, 0.04]]


def test_covariance_diagonal_fallback_for_missing_ticker() -> None:
    ents = {"risk_metrics": {"covariance": {"BBCA": {"BBCA": 0.04}}}}
    cov = _covariance(["BBCA", "NEWCO"], ents)
    assert cov[0][0] == 0.04
    assert cov[1][1] == _DEFAULT_VARIANCE   # NEWCO diagonal fallback
    assert cov[0][1] == 0.0 and cov[1][0] == 0.0
