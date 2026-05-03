from typing import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings


class ChatState(TypedDict):
    messages: list[BaseMessage]


# Singleton LLM instance
_llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=settings.OPENAI_API_KEY,
)


def chat_node(state: ChatState) -> ChatState:
    response = _llm.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}


def build_chat_graph():
    graph = StateGraph(ChatState)
    graph.add_node("chat", chat_node)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)
    return graph.compile(checkpointer=MemorySaver())


# Singleton graph instance
chat_graph = build_chat_graph()
