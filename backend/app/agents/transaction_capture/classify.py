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

_AMOUNT_PATTERN = re.compile(r"\b\d[\d.,]*\s*(rb|ribu|k|jt|juta|rp)\b", re.IGNORECASE)
_VERB_PATTERN = re.compile(
    r"\b(jual|beli|bayar|dapat|terima|keluar|masuk|laku|untung|rugi)\b", re.IGNORECASE,
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

    if has_amount and has_verb:
        return True
    if not has_amount and not has_verb:
        return False
    return _classify_with_llm(text)
