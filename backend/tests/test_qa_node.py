"""Tests for the reworked QA node (N8) — brainstorming persona with
conversation history and optional live market context.

The Gemini call is mocked; assertions are on WHAT the node sends to the
model (history preserved, context blocks attached) and how it degrades
when market data is unavailable."""
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.market.schemas import TickerSnapshot
from app.agents.qa import qa_node
from app.agents.state import new_state


def _mock_llm(captured: dict) -> MagicMock:
    llm = MagicMock()

    def _invoke(messages):
        captured["messages"] = messages
        return MagicMock(content="jawaban uji")

    llm.invoke.side_effect = _invoke
    return llm


def _state_with(messages, entities=None) -> dict:
    state = new_state()
    state["intent"] = "explain"
    state["messages"] = messages
    state["entities"] = entities or {}
    return state


def test_qa_forwards_conversation_history() -> None:
    captured: dict = {}
    state = _state_with([
        HumanMessage(content="apa itu RSI?"),
        AIMessage(content="RSI adalah indikator momentum."),
        HumanMessage(content="kalau dibanding MACD bagaimana?"),
    ])

    with patch("app.agents.qa.get_chat_model", return_value=_mock_llm(captured)):
        result = qa_node(state)

    sent = captured["messages"]
    assert isinstance(sent[0], SystemMessage)
    # prior turns preserved, in order, before the current question
    contents = [m.content for m in sent[1:]]
    assert contents[0] == "apa itu RSI?"
    assert contents[1] == "RSI adalah indikator momentum."
    assert "kalau dibanding MACD" in contents[-1]
    # answer appended to state
    assert result["messages"][-1].content == "jawaban uji"


def test_qa_attaches_market_context_for_extracted_tickers() -> None:
    captured: dict = {}
    state = _state_with(
        [HumanMessage(content="menurutmu prospek BBCA gimana?")],
        entities={"tickers": ["BBCA"]},
    )
    snapshot = TickerSnapshot(ticker="BBCA", last_close=9500.0, rsi14=55.0)

    with patch("app.agents.qa.get_chat_model", return_value=_mock_llm(captured)), \
         patch("app.agents.qa.build_ticker_snapshot", return_value=snapshot) as mock_snap:
        qa_node(state)

    mock_snap.assert_called_once_with("BBCA")
    final_prompt = captured["messages"][-1].content
    assert "KONTEKS DATA PASAR" in final_prompt
    assert "BBCA" in final_prompt
    assert "9500" in final_prompt


def test_qa_still_answers_when_market_fetch_fails() -> None:
    captured: dict = {}
    state = _state_with(
        [HumanMessage(content="menurutmu prospek BBCA gimana?")],
        entities={"tickers": ["BBCA"]},
    )

    with patch("app.agents.qa.get_chat_model", return_value=_mock_llm(captured)), \
         patch("app.agents.qa.build_ticker_snapshot", side_effect=RuntimeError("yf down")):
        result = qa_node(state)

    assert result["messages"][-1].content == "jawaban uji"
    assert "KONTEKS DATA PASAR" not in captured["messages"][-1].content


def test_qa_skips_market_fetch_without_tickers() -> None:
    captured: dict = {}
    state = _state_with([HumanMessage(content="apa itu inflasi?")])

    with patch("app.agents.qa.get_chat_model", return_value=_mock_llm(captured)), \
         patch("app.agents.qa.build_ticker_snapshot") as mock_snap:
        qa_node(state)

    mock_snap.assert_not_called()


def test_qa_falls_back_to_regex_ticker_detection() -> None:
    """No N1 entities, but the question names an all-caps 4-letter code."""
    captured: dict = {}
    state = _state_with([HumanMessage(content="bandingkan TLKM dengan sektor bank")])
    snapshot = TickerSnapshot(ticker="TLKM", last_close=3000.0)

    with patch("app.agents.qa.get_chat_model", return_value=_mock_llm(captured)), \
         patch("app.agents.qa.build_ticker_snapshot", return_value=snapshot) as mock_snap:
        qa_node(state)

    mock_snap.assert_called_once_with("TLKM")
    assert "KONTEKS DATA PASAR" in captured["messages"][-1].content


def test_qa_ignores_common_acronyms_in_regex_fallback() -> None:
    captured: dict = {}
    state = _state_with([HumanMessage(content="apa dampak POJK baru ke IHSG dan MACD?")])

    with patch("app.agents.qa.get_chat_model", return_value=_mock_llm(captured)), \
         patch("app.agents.qa.build_ticker_snapshot") as mock_snap:
        qa_node(state)

    mock_snap.assert_not_called()
