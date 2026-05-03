import uuid
from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage
from app.agents.chat_agent import chat_graph
from app.api.deps import get_current_user
from app.models.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    thread_id = request.thread_id or str(uuid.uuid4())

    result = chat_graph.invoke(
        {"messages": [HumanMessage(content=request.message)]},
        config={"configurable": {"thread_id": thread_id}},
    )

    last_message = result["messages"][-1]
    return ChatResponse(message=last_message.content, thread_id=thread_id)
