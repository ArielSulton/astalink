import pytest

# Skip the whole file if TA-Lib isn't installed locally — in Docker (Dockerfile.dev)
# the C library is built and the wrapper installed, so tests run there.
pytest.importorskip("talib")

from unittest.mock import MagicMock, patch

import numpy as np
from langchain_core.messages import AIMessage

from app.agents.market.node import market_node
from app.agents.state import new_state


def test_market_node_returns_snapshot_for_each_ticker() -> None:
    state = new_state()
    state["entities"] = {"tickers": ["BBCA", "BMRI"]}

    fake_closes = np.linspace(8000, 9000, 60)
    fake_news = []
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Indikator menunjukkan tren naik.")

    with patch("app.agents.market.node.fetch_close_prices", return_value=fake_closes), \
         patch("app.agents.market.node.fetch_news", return_value=fake_news), \
         patch("app.agents.market.node.get_chat_model", return_value=fake_llm):
        update = market_node(state)

    snapshot = update["entities"]["market_snapshot"]
    assert len(snapshot["tickers"]) == 2
    for t in snapshot["tickers"]:
        assert t["last_close"] is not None
        assert t["rsi14"] is not None
    assert snapshot["narration"]


def test_market_node_handles_empty_close_gracefully() -> None:
    """If yfinance returns nothing, ticker still appears in snapshot but with None metrics."""
    state = new_state()
    state["entities"] = {"tickers": ["XXXX"]}

    with patch("app.agents.market.node.fetch_close_prices", return_value=np.array([])), \
         patch("app.agents.market.node.fetch_news", return_value=[]), \
         patch("app.agents.market.node.get_chat_model"):
        update = market_node(state)

    t = update["entities"]["market_snapshot"]["tickers"][0]
    assert t["ticker"] == "XXXX"
    assert t["last_close"] is None
