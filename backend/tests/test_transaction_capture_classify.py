import os
from unittest.mock import patch

import pytest

from app.agents.transaction_capture.classify import (
    has_transaction_shape,
    looks_like_transaction,
)


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


@pytest.mark.skipif(
    not (os.getenv("GOOGLE_API_KEY") or os.getenv("SUMOPOD_API_KEY")),
    reason="requires a real LLM credential — this test calls the live classifier",
)
def test_looks_like_transaction_allocation_requests_are_not_misrouted() -> None:
    """Regression for a real bug found in final review: 'alokasikan 20 juta ke
    BBCA' and similar allocation/investment requests must never be classified
    as a business transaction, since they'd otherwise get captured as a fake
    transaction and brick the chatbot behind a bogus pending confirmation."""
    assert looks_like_transaction("alokasikan 20 juta ke BBCA") is False
    assert looks_like_transaction(
        "saya baru terima gaji 10 juta, enaknya dialokasikan kemana"
    ) is False


# --------------------------------------------------------------------------
# The user-facing variation matrix, asserted where it is deterministic.
# _classify_with_llm is patched to raise, so any case that quietly falls
# through to the model fails loudly instead of passing by luck.
# --------------------------------------------------------------------------

DETERMINISTIC_CASES = [
    ("saya baru saja menjual kopi 20.000 pada bisnis saya", True),
    ("jual kopi 20rb", True),
    ("menjual nasi goreng 15 ribu", True),
    ("beli bahan baku 200rb", True),
    ("bayar listrik Rp150.000", True),
    ("terima pembayaran catering 1.5jt", True),
    ("dapat untung 50rb hari ini", True),
    ("aku menjual kopi 20 ribu rupiah", True),
    ("aku barusan menjual kopi 20 pcs Rp 60.000", True),
    # no amount, no verb, no digit
    ("halo", False),
    ("bagaimana prospek IHSG minggu ini", False),
]

# Investment vocabulary deliberately never auto-decides on the amount+verb
# signal alone — "beli saham BBRI 50 juta" matches both patterns but is an
# advisory request, so classify.py always asks the model for a real judgment
# call. These must reach the LLM, and must respect its answer.
LLM_DEFERRED_CASES = [
    "alokasikan 20 juta ke saham BBCA",
    "beli saham BBRI 50 juta",
    "investasikan 10 juta di reksa dana",
]


@pytest.mark.parametrize("text", LLM_DEFERRED_CASES)
def test_investment_vocabulary_always_asks_the_llm(text: str) -> None:
    with patch("app.agents.transaction_capture.classify._classify_with_llm",
               return_value=False) as llm:
        assert looks_like_transaction(text) is False
    llm.assert_called_once()


def test_a_bare_quantity_is_not_an_amount() -> None:
    """"jual 20 pcs" is a count, not rupiah — a 1-3 digit bare number must
    not be enough to auto-route a message into capture."""
    assert has_transaction_shape("jual 20 pcs") is False
    assert has_transaction_shape("beli 3 karung") is False


@pytest.mark.parametrize("text,expected", DETERMINISTIC_CASES)
def test_looks_like_transaction_decides_the_matrix_without_the_llm(
    text: str, expected: bool,
) -> None:
    def _boom(_text):
        raise AssertionError(f"LLM fallback should not be reached for {_text!r}")

    with patch("app.agents.transaction_capture.classify._classify_with_llm", side_effect=_boom):
        assert looks_like_transaction(text) is expected


def test_ambiguous_phrasing_still_defers_to_the_llm() -> None:
    """Phrasings the regex vocabulary doesn't cover must consult the model
    rather than being silently dropped."""
    with patch("app.agents.transaction_capture.classify._classify_with_llm",
               return_value=True) as llm:
        assert looks_like_transaction("tadi ada yang ambil 3 bungkus") is True
    llm.assert_called_once()


def test_has_transaction_shape_is_llm_free() -> None:
    """Used to tell a user their workspace has no business without paying a
    model call on every ordinary advisory message."""
    assert has_transaction_shape("jual kopi 20rb") is True
    assert has_transaction_shape("aku menjual kopi 20 ribu rupiah") is True
    assert has_transaction_shape("beli bahan baku 200rb") is True
    assert has_transaction_shape("alokasikan 20 juta ke saham BBCA") is False
    assert has_transaction_shape("halo, apa kabar") is False
