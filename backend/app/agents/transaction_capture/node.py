"""Nodes for the transaction-capture subgraph: extraction, human
confirmation (via interrupt), and persistence of a confirmed or rejected
business transaction."""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from app.agents.transaction_capture.plausibility import compute_plausibility_flag
from app.agents.transaction_capture.schemas import TransactionExtraction
from app.agents.transaction_capture.state import TransactionCaptureState
from app.core.config import settings
from app.core.gemini import get_chat_model, get_vision_model
from app.core.metrics import track_node_duration
from app.core.supabase_admin import get_admin_client

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


@lru_cache(maxsize=None)
def _build_chain(source: str | None):
    """Photo/voice always go to Gemini (get_vision_model()) regardless of
    LLM_PROVIDER — see get_vision_model()'s docstring for why. Text
    extraction follows the same provider-specific structured-output method
    split as intent/node.py::_build_chain."""
    if source in ("whatsapp_photo", "whatsapp_voice"):
        return get_vision_model().with_structured_output(TransactionExtraction, method="json_schema")
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
    chain = _build_chain(state.get("source"))
    try:
        extraction: TransactionExtraction = chain.invoke([
            SystemMessage(content=EXTRACT_SYSTEM),
            HumanMessage(content=_build_content(state)),
        ])
    except Exception as exc:
        log.exception("transaction_capture.extract_node: extraction failed: %s", exc)
        return {"gate_failed": True, "extraction": None, "media_bytes": None, "media_mime_type": None}

    gate_failed = (
        (not extraction.is_transaction)
        or extraction.confidence < GATE_CONFIDENCE_THRESHOLD
        or extraction.amount is None
        or extraction.amount <= 0
        or extraction.type is None
    )
    return {
        "extraction": extraction.model_dump(),
        "gate_failed": gate_failed,
        # Never carry a binary payload past this node — it would otherwise
        # sit in Postgres checkpoint storage for the whole confirm-interrupt
        # pause, and no downstream node needs it.
        "media_bytes": None,
        "media_mime_type": None,
    }


@track_node_duration("transaction_capture_confirm")
def confirm_node(state: TransactionCaptureState) -> TransactionCaptureState:
    extraction = state["extraction"]
    plausibility_flag = compute_plausibility_flag(
        business_id=state["business_id"],
        type_=extraction["type"],
        amount=extraction["amount"],
    )

    row = get_admin_client().table("business_transactions").insert({
        "business_id": state["business_id"],
        "type": extraction["type"],
        "item_description": extraction["item_description"],
        "amount": extraction["amount"],
        "source": state["source"],
        "raw_input": extraction["raw_input"],
        "confidence": extraction["confidence"],
        "plausibility_flag": plausibility_flag,
        "status": "pending_confirmation",
    }).execute()
    transaction_id = row.data[0]["id"]

    resume = interrupt({
        "transaction_id": transaction_id,
        "item_description": extraction["item_description"],
        "amount": extraction["amount"],
        "type": extraction["type"],
        "plausibility_flag": plausibility_flag,
    })
    decision = resume.get("decision", "rejected")
    return {
        "confirmed": decision == "confirmed",
        "transaction_id": transaction_id,
        "plausibility_flag": plausibility_flag,
    }


def _upsert_financial_record(sb, *, business_id: str, type_: str, amount: float) -> None:
    year = datetime.now(timezone.utc).year
    omset_delta = amount if type_ == "income" else 0.0
    profit_delta = amount if type_ == "income" else -amount

    existing = (
        sb.table("business_financial_records").select("id,omset,profit")
        .eq("business_id", business_id).eq("period_year", year).execute()
    )
    rows = existing.data or []

    if rows:
        rec = rows[0]
        sb.table("business_financial_records").update({
            "omset": float(rec["omset"]) + omset_delta,
            "profit": float(rec["profit"]) + profit_delta,
        }).eq("id", rec["id"]).execute()
        return

    prior = (
        sb.table("business_financial_records").select("aset")
        .eq("business_id", business_id).order("period_year", desc=True).limit(1).execute()
    )
    prior_rows = prior.data or []
    carried_aset = float(prior_rows[0]["aset"]) if prior_rows else 0.0
    sb.table("business_financial_records").insert({
        "business_id": business_id,
        "period_year": year,
        "aset": carried_aset,
        "omset": omset_delta,
        "profit": profit_delta,
    }).execute()


@track_node_duration("transaction_capture_persist")
def persist_node(state: TransactionCaptureState) -> TransactionCaptureState:
    sb = get_admin_client()
    sb.table("business_transactions").update({
        "status": "confirmed",
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", state["transaction_id"]).execute()

    extraction = state["extraction"]
    _upsert_financial_record(
        sb, business_id=state["business_id"],
        type_=extraction["type"], amount=extraction["amount"],
    )
    return {}


@track_node_duration("transaction_capture_rejected")
def rejected_node(state: TransactionCaptureState) -> TransactionCaptureState:
    get_admin_client().table("business_transactions").update({
        "status": "rejected",
    }).eq("id", state["transaction_id"]).execute()
    return {}
