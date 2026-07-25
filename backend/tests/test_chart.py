import pytest

from app.integrations.chart import (
    render_allocation_chart,
    render_composition_chart,
    render_report_table_chart,
)


def test_render_allocation_chart_returns_valid_png() -> None:
    png = render_allocation_chart(
        weights=[{"ticker": "BBCA", "weight": 0.6}, {"ticker": "TLKM", "weight": 0.3}],
        cash_buffer=0.1,
    )
    assert isinstance(png, bytes)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")  # PNG magic bytes
    assert len(png) > 1000  # a real rendered image, not an empty/corrupt file


def test_render_allocation_chart_handles_zero_cash_buffer() -> None:
    png = render_allocation_chart(
        weights=[{"ticker": "BBCA", "weight": 1.0}],
        cash_buffer=0.0,
    )
    assert png.startswith(b"\x89PNG\r\n\x1a\n")


def test_render_allocation_chart_strips_jk_suffix_from_labels() -> None:
    """Just confirms this runs without error on .JK-suffixed tickers (the
    format yfinance/market_node actually use) — labels aren't otherwise
    inspectable from the rendered PNG bytes."""
    png = render_allocation_chart(
        weights=[{"ticker": "BBCA.JK", "weight": 0.5}, {"ticker": "TLKM.JK", "weight": 0.5}],
        cash_buffer=0.0,
    )
    assert png.startswith(b"\x89PNG\r\n\x1a\n")


def test_render_composition_chart_returns_valid_png() -> None:
    png = render_composition_chart(cash=0.25, stocks=0.25, business=0.5)
    assert isinstance(png, bytes)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 1000


def test_render_composition_chart_handles_zero_business() -> None:
    """A plain allocate_stocks composition (no business in the picture) —
    must still render fine with a 0% business slice."""
    png = render_composition_chart(cash=0.5, stocks=0.5, business=0.0)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")


def _verdict(ticker: str, band: str = "buy", score: float = 70.0) -> dict:
    return {"ticker": ticker, "band": band, "score": score, "gate_status": "pass"}


def test_render_report_table_chart_with_both_tables() -> None:
    png = render_report_table_chart(
        verdicts={"BBCA": _verdict("BBCA")},
        weights=[{"ticker": "BBCA", "weight": 0.6}, {"ticker": "TLKM", "weight": 0.4}],
    )
    assert isinstance(png, bytes)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 1000


def test_render_report_table_chart_verdicts_only() -> None:
    png = render_report_table_chart(verdicts={"BBCA": _verdict("BBCA")}, weights=[])
    assert png.startswith(b"\x89PNG\r\n\x1a\n")


def test_render_report_table_chart_weights_only() -> None:
    png = render_report_table_chart(verdicts={}, weights=[{"ticker": "BBCA", "weight": 1.0}])
    assert png.startswith(b"\x89PNG\r\n\x1a\n")


def test_render_report_table_chart_raises_when_both_empty() -> None:
    with pytest.raises(ValueError):
        render_report_table_chart(verdicts={}, weights=[])
