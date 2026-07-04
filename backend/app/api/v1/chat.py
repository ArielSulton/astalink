import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import HumanMessage
from app.agents.chat_agent import build_chat_reply
from app.agents.graph import graph
from app.agents.state import new_state
from app.api.deps import get_current_user
from app.core.ownership import assert_workspace_owned
from app.core.supabase_admin import get_admin_client
from app.models.chat import ChatRequest, ChatResponse

router = APIRouter()


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
    initial["messages"] = [HumanMessage(content=request.message)]
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

    return ChatResponse(message=build_chat_reply(final_state), thread_id=raw_thread)
