from unittest.mock import patch

from app.agents.transaction_capture.classify import looks_like_transaction


def test_looks_like_transaction_true_for_amount_and_verb() -> None:
    assert looks_like_transaction("jual nasi goreng 15rb") is True
    assert looks_like_transaction("beli bahan baku 200 ribu") is True
    assert looks_like_transaction("dapat 50rb dari pelanggan") is True


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


def test_looks_like_transaction_investment_instruction_falls_back_to_llm() -> None:
    """'beli saham BBCA 10 juta' matches both the amount and verb patterns,
    but it's an ordinary investment-advisory request in this app, not a
    business transaction — investment vocabulary must force the LLM
    fallback rather than an automatic True."""
    with patch("app.agents.transaction_capture.classify._classify_with_llm", return_value=False) as llm_mock:
        looks_like_transaction("beli saham BBCA 10 juta")
    llm_mock.assert_called_once()


def test_looks_like_transaction_business_sale_without_investment_vocab_still_short_circuits() -> None:
    """Must not regress: an ordinary business sale with no investment
    vocabulary still auto-returns True without ever consulting the LLM."""
    with patch("app.agents.transaction_capture.classify._classify_with_llm") as llm_mock:
        assert looks_like_transaction("jual nasi goreng 15rb") is True
    llm_mock.assert_not_called()


def test_looks_like_transaction_true_for_rp_prefix_amount_and_conjugated_verb() -> None:
    """Regression for the exact reported failure: 'Aku barusan menjual kopi
    20 pcs, seharga Rp 60.000' matched neither the old suffix-only amount
    pattern (Rp comes BEFORE the digits) nor the old bare-root verb pattern
    ('menjual' has no word boundary before 'jual', since the me- prefix
    attaches directly) — so it silently fell through to the advisory graph
    instead of being captured."""
    with patch("app.agents.transaction_capture.classify._classify_with_llm") as llm_mock:
        assert looks_like_transaction("Aku barusan menjual kopi 20 pcs, seharga Rp 60.000") is True
    llm_mock.assert_not_called()


def test_looks_like_transaction_true_for_other_conjugated_verbs() -> None:
    assert looks_like_transaction("saya membayar Rp 25.000 untuk bahan baku") is True
    assert looks_like_transaction("baru saja terjual 3 bungkus kopi 15rb") is True


def test_looks_like_transaction_falls_back_to_llm_when_digit_present_but_no_signal_matches() -> None:
    """A digit alone isn't enough for an automatic decision, but it must not
    be silently dropped either — falls back to the LLM instead of a hard
    False."""
    with patch("app.agents.transaction_capture.classify._classify_with_llm", return_value=False) as llm_mock:
        assert looks_like_transaction("ada pelanggan nomor 8 komplain soal produk") is False
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
