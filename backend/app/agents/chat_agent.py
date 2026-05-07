from typing import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings


class ChatState(TypedDict):
    messages: list[BaseMessage]


# Lazy singleton — not instantiated at import time so the app boots even when
# OPENAI_API_KEY is absent (T10 will migrate this to Gemini).
_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
        )
    return _llm


def chat_node(state: ChatState) -> ChatState:
    response = _get_llm().invoke(state["messages"])
    return {"messages": state["messages"] + [response]}


def build_chat_graph():
    graph = StateGraph(ChatState)
    graph.add_node("chat", chat_node)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)
    return graph.compile(checkpointer=MemorySaver())


# Singleton graph instance
chat_graph = build_chat_graph()
