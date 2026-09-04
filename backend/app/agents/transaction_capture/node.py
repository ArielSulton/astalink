"""Nodes for the standalone transaction-capture subgraph. extract_node is
defined in this task; confirm_node/persist_node/rejected_node are appended
by the next task in this same file."""
from __future__ import annotations

import base64
import logging
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.transaction_capture.schemas import TransactionExtraction
from app.agents.transaction_capture.state import TransactionCaptureState
from app.core.config import settings
from app.core.gemini import get_chat_model
from app.core.metrics import track_node_duration

log = logging.getLogger(__name__)

GATE_CONFIDENCE_THRESHOLD = 0.5

EXTRACT_SYSTEM = """\
You extract a single business transaction from a WhatsApp message sent by \
an Indonesian UMKM (micro/small business) owner. The message may be plain \
text, a transcript of a voice note, or a photo of a receipt/note.

Only extract what is actually stated — never guess or invent a plausible \
number. If the message is not a transaction at all (a greeting, a question, \
small talk), set is_transaction=false and leave item_description/amount/type \
null. If it IS a transaction but some field is unclear, leave that field \
null rather than guessing.

`type` is "income" for a sale/money received, "expense" for a purchase/cost \
paid. `raw_input` must be your transcription/reading of the original \
content verbatim (the spoken words for audio, the visible text for a \
photo, or the message itself for plain text). Estimate confidence (0-1) \
honestly — a clear, unambiguous transaction should score high; anything \
you had to guess at should score low.

Respond with a single JSON object matching this shape, and nothing else:
{"is_transaction": <bool>, "item_description": <string or null>, \
"amount": <number or null>, "type": "income"|"expense"|null, \
"confidence": <0-1>, "raw_input": "<string>"}
"""


@lru_cache(maxsize=1)
def _build_chain():
    """Same provider-specific structured-output method split as
    intent/node.py::_build_chain — see that module's docstring for why."""
    llm = get_chat_model()
    method = "function_calling" if settings.LLM_PROVIDER == "sumopod" else "json_schema"
    return llm.with_structured_output(TransactionExtraction, method=method)


def _build_content(state: TransactionCaptureState) -> list[dict]:
    if state.get("source") == "whatsapp_text":
        return [{"type": "text", "text": state.get("text_body") or ""}]

    media_bytes = state.get("media_bytes") or b""
    b64 = base64.b64encode(media_bytes).decode()
    return [
        {"type": "text", "text": "Ekstrak transaksi dari lampiran ini."},
        {
            "type": "media",
            "mime_type": state.get("media_mime_type") or "application/octet-stream",
            "data": b64,
        },
    ]


@track_node_duration("transaction_capture_extract")
def extract_node(state: TransactionCaptureState) -> TransactionCaptureState:
    chain = _build_chain()
    try:
        extraction: TransactionExtraction = chain.invoke([
            SystemMessage(content=EXTRACT_SYSTEM),
            HumanMessage(content=_build_content(state)),
        ])
    except Exception as exc:
        log.error("transaction_capture.extract_node: extraction failed: %s", exc)
        return {"gate_failed": True, "extraction": None, "media_bytes": None, "media_mime_type": None}

    gate_failed = (not extraction.is_transaction) or extraction.confidence < GATE_CONFIDENCE_THRESHOLD
    return {
        "extraction": extraction.model_dump(),
        "gate_failed": gate_failed,
        # Never carry a binary payload past this node — it would otherwise
        # sit in Postgres checkpoint storage for the whole confirm-interrupt
        # pause, and no downstream node needs it.
        "media_bytes": None,
        "media_mime_type": None,
    }
