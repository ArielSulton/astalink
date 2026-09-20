from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.context_snapshot import WorkspaceSnapshot
from app.agents.reply_writer import (
    FALLBACKS,
    MAX_HISTORY,
    DeadEndReason,
    compose_dead_end_reply,
)
from app.agents.state import new_state


def _state_with_history(n: int) -> dict:
    state = new_state()
    messages = []
    for i in range(n):
        messages.append(HumanMessage(content=f"pesan user {i}"))
        messages.append(AIMessage(content=f"jawaban {i}"))
    state["messages"] = messages
    return state


def test_every_reason_has_a_static_fallback() -> None:
    """Contract test: a new DeadEndReason must not ship without a canned
    sentence, or a Gemini outage would leave the user with nothing."""
    for reason in DeadEndReason:
        assert FALLBACKS[reason].strip()


def test_falls_back_when_llm_raises() -> None:
    with patch("app.agents.reply_writer.get_chat_model",
               side_effect=RuntimeError("gemini down")):
        reply = compose_dead_end_reply(
            reason=DeadEndReason.LOW_CONFIDENCE,
            state=new_state(),
        )

    assert reply == FALLBACKS[DeadEndReason.LOW_CONFIDENCE]


def test_falls_back_when_llm_returns_blank() -> None:
    model = MagicMock()
    model.invoke.return_value = MagicMock(content="   ")

    with patch("app.agents.reply_writer.get_chat_model", return_value=model):
        reply = compose_dead_end_reply(
            reason=DeadEndReason.QA_EMPTY_ANSWER,
            state=new_state(),
        )

    assert reply == FALLBACKS[DeadEndReason.QA_EMPTY_ANSWER]


def test_explicit_fallback_overrides_registry() -> None:
    with patch("app.agents.reply_writer.get_chat_model",
               side_effect=RuntimeError("gemini down")):
        reply = compose_dead_end_reply(
            reason=DeadEndReason.LOW_CONFIDENCE,
            state=new_state(),
            fallback="cadangan khusus",
        )

    assert reply == "cadangan khusus"


def test_prompt_carries_every_fact_and_the_snapshot() -> None:
    model = MagicMock()
    model.invoke.return_value = MagicMock(content="Balasan dinamis.")
    snapshot = WorkspaceSnapshot(cash_balance=12_400_000)

    with patch("app.agents.reply_writer.get_chat_model", return_value=model):
        reply = compose_dead_end_reply(
            reason=DeadEndReason.LOW_CONFIDENCE,
            state=new_state(),
            snapshot=snapshot,
            facts={"catatan_ambiguitas": "tidak jelas nominalnya"},
        )

    assert reply == "Balasan dinamis."
    sent = model.invoke.call_args[0][0]
    blob = "\n".join(str(m.content) for m in sent)
    assert "tidak jelas nominalnya" in blob
    assert "Rp 12.400.000" in blob
    assert "dilarang" in blob.lower()


def test_prompt_includes_only_the_last_ten_turns() -> None:
    model = MagicMock()
    model.invoke.return_value = MagicMock(content="Balasan.")

    with patch("app.agents.reply_writer.get_chat_model", return_value=model):
        compose_dead_end_reply(
            reason=DeadEndReason.QA_NO_QUESTION,
            state=_state_with_history(12),
        )

    sent = model.invoke.call_args[0][0]
    history = [m for m in sent if isinstance(m, (HumanMessage, AIMessage))]
    # at most MAX_HISTORY history turns + the one situation turn
    assert len(history) <= MAX_HISTORY + 1
    blob = "\n".join(str(m.content) for m in sent)
    assert "pesan user 11" in blob
    assert "pesan user 0" not in blob


def test_reply_is_trimmed_to_three_sentences() -> None:
    model = MagicMock()
    model.invoke.return_value = MagicMock(
        content="Satu. Dua. Tiga. Empat. Lima.")

    with patch("app.agents.reply_writer.get_chat_model", return_value=model):
        reply = compose_dead_end_reply(
            reason=DeadEndReason.PORTFOLIO_STATUS_UNAVAILABLE,
            state=new_state(),
        )

    assert reply == "Satu. Dua. Tiga."
