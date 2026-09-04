"""State for the standalone transaction-capture subgraph — deliberately NOT
AgentState (the main advisory graph's state). This flow has no reason to
share 20+ unrelated advisory fields; it has its own thread namespace
(wa-txn-{phone}-{workspace_id}) and its own small state shape.

media_bytes/media_mime_type are only populated on the initial invoke (by
the webhook handler, after downloading a photo/voice note) and are always
cleared by extract_node before the state is checkpointed at the confirm
interrupt — large binary payloads have no reason to sit in Postgres
checkpoint storage past the node that actually needs them."""
from __future__ import annotations

from typing import Literal, TypedDict


class TransactionCaptureState(TypedDict, total=False):
    business_id: str
    workspace_id: str
    phone_e164: str
    source: Literal["whatsapp_text", "whatsapp_voice", "whatsapp_photo"]
    text_body: str | None
    media_bytes: bytes | None
    media_mime_type: str | None
    extraction: dict | None
    gate_failed: bool
    plausibility_flag: bool
    transaction_id: str | None
    confirmed: bool | None
