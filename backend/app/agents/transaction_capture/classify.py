"""Cheap router for ambiguous plain-text WhatsApp messages — decides
whether this looks like a business-transaction record (route to capture)
or not (fall through to the advisory graph unchanged). Deliberately
independent of N1's intent taxonomy (app/agents/intent/node.py) — see
spec's "Routing" section for why the two must stay decoupled."""
from __future__ import annotations

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.gemini import extract_text, get_chat_model

log = logging.getLogger(__name__)

_AMOUNT_PATTERN = re.compile(
    r"\b\d[\d.,]*\s*(?:rb|ribu|k|jt|juta|rp)\b"  # suffix form: "15rb", "200 ribu", "3jt"
    r"|\b(?:rp|rupiah)\.?\s*\d[\d.,]*",           # prefix form: "Rp 60.000", "rupiah 60000"
    re.IGNORECASE,
)
# Root-word forms plus the common meN-/di-/ter- conjugations Indonesian
# speakers actually use in a sentence ("menjual", not just "jual") — a bare
# \b-bounded root never matches its own prefixed form, since the prefix
# attaches with no space (no word boundary appears between them).
_VERB_PATTERN = re.compile(
    r"\b(jual|menjual|dijual|terjual|jualan|"
    r"beli|membeli|dibeli|terbeli|"
    r"bayar|membayar|dibayar|terbayar|"
    r"dapat|mendapat|mendapatkan|didapat|"
    r"terima|menerima|diterima|"
    r"keluar|mengeluarkan|"
    r"masuk|memasukkan|"
    r"laku|laris|"
    r"untung|keuntungan|menguntungkan|"
    r"rugi|kerugian|merugikan)\b",
    re.IGNORECASE,
)
_HAS_DIGIT_PATTERN = re.compile(r"\d")
# Investment-advisory vocabulary. "beli saham BBCA 10 juta" and "jual BBRI 50
# juta" match both _AMOUNT_PATTERN and _VERB_PATTERN, but they're ordinary
# advisory requests in this app, not business-transaction records — when
# this vocabulary is present, never auto-return True on the amount+verb
# signal alone; always fall through to the LLM for a real judgment call.
_INVESTMENT_VOCAB_PATTERN = re.compile(
    r"\b(saham|emas|reksa\s?dana|obligasi|investasi|portofolio|alokasi|ihsg|deposito)\b",
    re.IGNORECASE,
)

_LLM_SYSTEM = """\
Answer with exactly one word, "ya" or "tidak": does this WhatsApp message \
record a specific business transaction (a sale or an expense with an \
amount), as opposed to a general question, comment, or investment-advisory \
request? Reply "ya" only if it's clearly recording something that happened."""


def _classify_with_llm(text: str) -> bool:
    try:
        resp = get_chat_model().invoke([
            SystemMessage(content=_LLM_SYSTEM),
            HumanMessage(content=text),
        ])
    except Exception as exc:
        log.error("classify._classify_with_llm failed: %s", exc)
        return False
    return extract_text(resp.content).strip().lower().startswith("ya")


def looks_like_transaction(text: str) -> bool:
    has_amount = bool(_AMOUNT_PATTERN.search(text))
    has_verb = bool(_VERB_PATTERN.search(text))

    if has_amount and has_verb and not _INVESTMENT_VOCAB_PATTERN.search(text):
        return True
    if not has_amount and not has_verb and not _HAS_DIGIT_PATTERN.search(text):
        # No amount/verb signal at all, and not even a bare digit anywhere —
        # unambiguously not a transaction. A digit alone doesn't clear the
        # bar for an automatic decision, but it's enough reason to consult
        # the LLM rather than silently drop a message our regex vocabulary
        # simply doesn't cover yet.
        return False
    return _classify_with_llm(text)
