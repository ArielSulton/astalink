from typing import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.core.gemini import get_chat_model


class ChatState(TypedDict):
    messages: list[BaseMessage]


def chat_node(state: ChatState) -> ChatState:
    llm = get_chat_model()
    response = llm.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}


def build_chat_graph():
    graph = StateGraph(ChatState)
    graph.add_node("chat", chat_node)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)
    return graph.compile(checkpointer=MemorySaver())


# Singleton graph instance — graph compilation is cheap; the LLM is lazy.
chat_graph = build_chat_graph()
