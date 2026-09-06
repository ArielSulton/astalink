from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    workspace_id: str
    thread_id: str | None = None
    # Base64-encoded receipt photo, optional. When present, routes to
    # transaction-capture's photo path instead of the advisory graph —
    # see chat.py::chat()'s transaction-capture routing stage.
    photo_base64: str | None = None
    photo_mime_type: str | None = None


class ChatResponse(BaseModel):
    message: str
    thread_id: str
    # Allocation runs only: lets the chat UI render an Approvals CTA instead
    # of relying on the user to find the audit id inside the message text.
    audit_id: str | None = None
    requires_approval: bool = False
    intent: str | None = None
    # True while paused at the composition gate (allocate_capital only),
    # waiting for a ya/tidak reply in the NEXT message on this same thread.
    awaiting_composition_approval: bool = False
    # Layer 0's cash/stocks/business split — lets the chat UI render the same
    # visual AllocationBar the dashboard shows, instead of leaving the split
    # as plain text inside `message`.
    layer0_result: dict[str, Any] | None = None
    # Present only while a transaction-capture confirmation is pending on
    # this thread — {transaction_id, item_description, amount, type,
    # plausibility_flag}, same shape as the WhatsApp interrupt payload.
    pending_transaction: dict[str, Any] | None = None
    # True when a capture attempt (photo or text) was blocked because the
    # workspace doesn't own exactly one business — the frontend should
    # offer a CTA to /business.
    requires_business_setup: bool = False
