# backend/tests/test_news_endpoint.py
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.agents.market.schemas import NewsItem

client = TestClient(app)

MOCK_ARTICLES = [
    NewsItem(title="BBCA posts record profit", source="Reuters",
             published_at="2026-06-20T10:00:00Z", sentiment="positive"),
    NewsItem(title="IDX market steady", source="Bloomberg",
             published_at="2026-06-20T09:00:00Z", sentiment="neutral"),
]

def test_news_returns_structure():
    with patch("app.api.v1.market.fetch_news", return_value=MOCK_ARTICLES):
        resp = client.get("/api/v1/market/news?ticker=BBCA.JK")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "BBCA.JK"
    assert len(data["articles"]) == 2
    assert data["articles"][0]["sentiment"] == "positive"

def test_news_empty_when_key_missing():
    with patch("app.api.v1.market.fetch_news", return_value=[]):
        resp = client.get("/api/v1/market/news?ticker=TLKM.JK")
    assert resp.status_code == 200
    assert resp.json()["articles"] == []
    assert resp.json()["ticker"] == "TLKM.JK"
