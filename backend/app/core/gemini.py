"""Lazy singleton Gemini chat client.

Construction is deferred to first use so the backend can boot even when
GOOGLE_API_KEY is unset (e.g. during partial-config dev work). Failures
surface only when a caller actually invokes the model.

Embeddings are handled by Pinecone's integrated inference (index-side
multilingual-e5-large) — see app.core.pinecone — not by Gemini."""
from __future__ import annotations

from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

_chat_model: ChatGoogleGenerativeAI | None = None


def get_chat_model() -> ChatGoogleGenerativeAI:
    global _chat_model
    if _chat_model is None:
        _chat_model = ChatGoogleGenerativeAI(
            model=settings.GEMINI_CHAT_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0,
        )
    return _chat_model


def extract_text(content: Any) -> str:
    """Normalize an AIMessage.content payload to plain text.

    Newer Gemini models (anything past gemini-1.5-flash) return content as a
    list of content blocks (``[{"type": "text", "text": "..."}]``) instead of
    a bare string; older ones return a plain string. Every narration/JSON
    call site expects a string, so normalize here once instead of each
    caller guessing at the shape."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content) if content else ""
