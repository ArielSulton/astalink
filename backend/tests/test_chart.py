from app.integrations.chart import render_allocation_chart


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
