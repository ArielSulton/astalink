from unittest.mock import MagicMock, patch

from app.agents.transaction_capture.classify import looks_like_transaction


def test_looks_like_transaction_true_for_amount_and_verb() -> None:
    assert looks_like_transaction("jual nasi goreng 15rb") is True
    assert looks_like_transaction("beli bahan baku 200 ribu") is True
    assert looks_like_transaction("dapat Rp50.000 dari pelanggan") is True


def test_looks_like_transaction_false_for_neither_signal() -> None:
    """No amount, no transaction verb — must never fall back to an LLM call
    for something this unambiguous."""
    with patch("app.agents.transaction_capture.classify._classify_with_llm") as llm_mock:
        assert looks_like_transaction("halo, apa kabar?") is False
    llm_mock.assert_not_called()


def test_looks_like_transaction_falls_back_to_llm_when_ambiguous() -> None:
    """Has an amount but no clear verb: ambiguous, must consult the LLM
    fallback rather than guess."""
    with patch("app.agents.transaction_capture.classify._classify_with_llm", return_value=True) as llm_mock:
        assert looks_like_transaction("15rb tadi") is True
    llm_mock.assert_called_once()


def test_looks_like_transaction_advisory_question_is_not_misrouted() -> None:
    """'bisnis warung saya lagi rame, pengaruhnya ke rekomendasi gimana?' has
    neither an amount+item pattern — must fall through to the advisory
    flow, not capture."""
    with patch("app.agents.transaction_capture.classify._classify_with_llm") as llm_mock:
        assert looks_like_transaction(
            "bisnis warung saya lagi rame, pengaruhnya ke rekomendasi gimana?"
        ) is False
    llm_mock.assert_not_called()
