"""Regression test for a cross-turn ticker leak.

`entities` is merged across turns on the same LangGraph thread via an
``operator.or_`` reducer (see app/agents/state.py) — keys this turn's node
updates don't touch keep whatever a *previous* turn on that thread left
behind. WhatsApp threads never rotate (`wa-{phone}-{workspace_id}`), so a
prior turn's `eligible_tickers`/`stock_engine` (computed for a different
ticker) can still be sitting in `entities` when this turn starts. If this
turn's stock engine call fails, market_node must not silently leave that
stale data in place — optimizer_node prefers `eligible_tickers` over
`entities.tickers`, so a stale value there makes the whole pipeline analyze
the wrong ticker.
"""
from unittest.mock import MagicMock, patch

import numpy as np
from langchain_core.messages import AIMessage

from app.agents.market.node import market_node
from app.agents.state import new_state


def test_market_node_clears_stale_eligible_tickers_on_engine_failure() -> None:
    state = new_state()
    state["layer0_result"] = {"allocation": {"stocks": 0.5, "cash": 0.3, "business": 0.2}}
    # Simulates a prior turn on the same (permanent WhatsApp) thread having
    # analyzed BBCA — left behind by the operator.or_ reducer even though
    # this turn asks about TLKM.
    state["entities"] = {
        "tickers": ["TLKM"],
        "eligible_tickers": ["BBCA"],
        "stock_engine": {"verdicts": {"BBCA": "BUY"}, "eligible_tickers": ["BBCA"]},
    }

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="ringkasan")

    with patch("app.agents.market.node.fetch_close_prices", return_value=np.array([])), \
         patch("app.agents.market.node.fetch_news", return_value=[]), \
         patch("app.agents.market.node.get_chat_model", return_value=fake_llm), \
         patch("app.agents.market.stock_engine.run_stock_engine",
               side_effect=RuntimeError("boom")):
        update = market_node(state)

    entities = update["entities"]
    assert entities.get("eligible_tickers") is None
    assert entities.get("stock_engine") is None
