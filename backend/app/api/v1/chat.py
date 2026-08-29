import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import AIMessage, HumanMessage
from app.agents.chat_agent import build_chat_reply
from app.agents.composition_gate.resume import (
    detect_composition_reply,
    find_pending_composition_audit,
    resume_composition,
)
from app.agents.graph import graph
from app.agents.state import new_state
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

    # A message on a thread that's paused at the composition gate is treated
    # as a reply to it ("ya"/"tidak") rather than a brand new turn, as long
    # as it's a clear yes/no — anything else falls through to a fresh turn.
    pending_audit = find_pending_composition_audit(get_admin_client(), thread_id)
    reply = detect_composition_reply(request.message) if pending_audit else None

    if reply is not None:
        final_state = resume_composition(thread_id, reply)
    else:
        initial = new_state()
        initial["messages"] = [*load_thread_history(thread_id),
                               HumanMessage(content=request.message)]
        initial["_user_id"] = user_sub
        initial["_workspace_id"] = request.workspace_id
        initial["_thread_id"] = thread_id
        initial["entities"] = {"workspace_id": request.workspace_id}

        final_state = graph.invoke(
            initial, config={"configurable": {"thread_id": thread_id}},
        )

    if not final_state.get("messages"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent produced no response",
        )

    # Advisory mode: the pipeline produces reports and recommendations only.
    # No HITL approval or automatic execution — the user decides.
    requires_approval = False

    reply_text = build_chat_reply(final_state, style="report")

    # build_chat_reply's output (the report/prompt actually shown to the
    # user) is computed from final_state on every call — it is NEVER itself
    # appended to state["messages"] by any graph node for the allocation
    # path (l0_allocation -> ... -> legal -> END never writes a final
    # AIMessage; only n8_qa's informational path does). Without persisting
    # it here, load_thread_history() on the next turn sees only the user's
    # messages with no record of what AstaLink actually said — so a genuine
    # follow-up ("kenapa alokasi bisnis 0%?") has no report text in its
    # context to refer back to, and gets misclassified as a fresh request
    # instead of the intent_node history fix (see intent/node.py's
    # _history()) ever getting a chance to help. Persist explicitly so every
    # channel's actual reply becomes real conversation history.
    try:
        graph.update_state(
            config={"configurable": {"thread_id": thread_id}},
            values={"messages": [*final_state.get("messages", []),
                                 AIMessage(content=reply_text)]},
        )
    except Exception:
        log.exception("chat: failed to persist reply to thread %s", thread_id)

    return ChatResponse(
        message=reply_text,
        thread_id=raw_thread,
        audit_id=final_state.get("audit_id"),
        requires_approval=requires_approval,
        intent=final_state.get("intent"),
        awaiting_composition_approval=bool(final_state.get("__interrupt__")),
        layer0_result=final_state.get("layer0_result"),
    )
