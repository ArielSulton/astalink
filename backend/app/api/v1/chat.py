import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import HumanMessage
from app.agents.chat_agent import build_chat_reply
from app.agents.graph import graph
from app.agents.intents import Intent
from app.agents.state import LegalStatus, new_state
from app.api.deps import get_current_user
from app.core.ownership import assert_workspace_owned
from app.core.supabase_admin import get_admin_client
from app.models.chat import ChatRequest, ChatResponse

log = logging.getLogger(__name__)
router = APIRouter()

# Prior turns re-sent to the graph on a continued thread. The `messages`
# channel has no reducer (nodes overwrite-append), so history must be
# prepended here at the entry point or the QA node never sees it.
MAX_HISTORY = 20


def load_thread_history(thread_id: str) -> list:
    """Best-effort prior messages for a thread; empty list on any failure."""
    try:
        snapshot = graph.get_state(config={"configurable": {"thread_id": thread_id}})
        messages = (snapshot.values or {}).get("messages") or []
        return list(messages)[-MAX_HISTORY:]
    except Exception:  # noqa: BLE001 — history is optional, never fail the turn
        log.warning("chat: could not load history for thread %s", thread_id, exc_info=True)
        return []


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    # Scope thread_id to the authenticated user to prevent cross-user access
    user_sub = current_user["sub"]
    raw_thread = request.thread_id or str(uuid.uuid4())
    thread_id = f"{user_sub}:{raw_thread}"

    assert_workspace_owned(get_admin_client(), request.workspace_id, user_sub)

    initial = new_state()
    initial["messages"] = [*load_thread_history(thread_id),
                           HumanMessage(content=request.message)]
    initial["_user_id"] = user_sub
    initial["_workspace_id"] = request.workspace_id
    initial["entities"] = {"workspace_id": request.workspace_id}

    final_state = graph.invoke(
        initial, config={"configurable": {"thread_id": thread_id}},
    )

    if not final_state.get("messages"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent produced no response",
        )

    # Same state-shape check the WhatsApp handler uses: only an allocation
    # paused at HITL (legal ok, no human decision yet) has anything to approve.
    # Scoped to allocation intents so a leftover legal_status on a continued
    # thread can't attach an Approvals CTA to a plain Q&A answer.
    requires_approval = (
        final_state.get("intent") in (Intent.ALLOCATE_STOCKS.value,
                                      Intent.ALLOCATE_CAPITAL.value)
        and final_state.get("legal_status") in (LegalStatus.APPROVED, LegalStatus.PARTIAL)
        and final_state.get("user_approval") is None
    )

    return ChatResponse(
        message=build_chat_reply(final_state, style="report"),
        thread_id=raw_thread,
        audit_id=final_state.get("audit_id"),
        requires_approval=requires_approval,
        intent=final_state.get("intent"),
    )
