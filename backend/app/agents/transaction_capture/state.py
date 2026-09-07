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
    # Every business the caller's workspace owns, [{"id", "name"}, …]. The
    # graph resolves ONE of them in resolve_business_node rather than having
    # the caller pick, because picking may require asking the user — which
    # only a node can do (it needs interrupt()).
    candidate_businesses: list[dict]
    # Set by WhatsApp's "ganti bisnis": ignore whatever business_id this
    # thread already remembers and ask again.
    force_business_choice: bool
    # Resolved by resolve_business_node, not supplied by the caller. On a
    # thread that has captured before, the previous run's value survives in
    # the checkpoint and is what "remember the last choice per conversation"
    # reads — see the spec's "Remembering the choice" section.
    business_id: str | None
    business_name: str | None
    # True when the user answered the business question with "Batalkan" —
    # routes straight to END, before any row is written.
    business_cancelled: bool
    # WhatsApp only. Set when the user types "ganti bisnis" outside any
    # transaction: the bot lists the businesses immediately and the NEXT
    # message is read as the answer. The web has no equivalent — a new chat
    # room is a new thread, which forgets on its own.
    awaiting_business_preselect: bool
    workspace_id: str
    phone_e164: str
    source: Literal[
        "whatsapp_text", "whatsapp_voice", "whatsapp_photo",
        "web_text", "web_photo",
    ]
    text_body: str | None
    media_bytes: bytes | None
    media_mime_type: str | None
    extraction: dict | None
    gate_failed: bool
    plausibility_flag: bool
    transaction_id: str | None
    confirmed: bool | None
