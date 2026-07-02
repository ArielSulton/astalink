from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


FAKE_SERIES = [{"date": "2025-01-01", "close": 9500.0, "sma20": 9400.0, "ema50": 9350.0, "rsi14": 55.0}]

FAKE_TICKER_DATA = {
    "series": FAKE_SERIES,
    "last_close": 9500.0,
    "prev_close": 9400.0,
    "rsi14": 55.0,
    "sma20": 9400.0,
    "macd": 12.0,
    "bb_upper": 10000.0,
    "bb_lower": 9000.0,
}

FAKE_USER = {"sub": "test-user-id"}
AUTH_HEADERS = {"Authorization": "Bearer test-token"}


def test_watchlist_returns_list(client: TestClient) -> None:
    with patch("app.api.deps.verify_token", return_value=FAKE_USER), \
         patch(
             "app.api.v1.market.fetch_price_series_with_indicators",
             return_value=FAKE_TICKER_DATA,
         ):
        response = client.get("/api/v1/market/watchlist?tickers=BBCA.JK", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    item = data[0]
    assert item["ticker"] == "BBCA.JK"
    assert item["last_close"] == 9500.0
    assert item["price_change_pct"] == pytest.approx(1.0638, abs=0.01)
    assert len(item["price_series"]) == 1
    assert item["price_series"][0]["date"] == "2025-01-01"


def test_watchlist_default_tickers(client: TestClient) -> None:
    with patch("app.api.deps.verify_token", return_value=FAKE_USER), \
         patch(
             "app.api.v1.market.fetch_price_series_with_indicators",
             return_value=FAKE_TICKER_DATA,
         ):
        response = client.get("/api/v1/market/watchlist", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert len(response.json()) == 4  # default: BBCA.JK, TLKM.JK, ASII.JK, BBRI.JK
