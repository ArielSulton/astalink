from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    workspace_id: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    message: str
    thread_id: str
    # Allocation runs only: lets the chat UI render an Approvals CTA instead
    # of relying on the user to find the audit id inside the message text.
    audit_id: str | None = None
    requires_approval: bool = False
    intent: str | None = None
