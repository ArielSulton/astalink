"""Lazy singleton chat client — Gemini or SumoPod, switchable via
settings.LLM_PROVIDER.

Construction is deferred to first use so the backend can boot even when
GOOGLE_API_KEY/SUMOPOD_API_KEY is unset (e.g. during partial-config dev
work). Failures surface only when a caller actually invokes the model.

Embeddings are handled by Pinecone's integrated inference (index-side
multilingual-e5-large) — see app.core.pinecone — not by this client."""
from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.core.config import settings

_chat_model: BaseChatModel | None = None


def get_chat_model() -> BaseChatModel:
    global _chat_model
    if _chat_model is None:
        if settings.LLM_PROVIDER == "sumopod":
            # SumoPod is an OpenAI-compatible proxy (e.g. fronting DeepSeek) —
            # same client class OpenAI itself uses, just pointed elsewhere.
            _chat_model = ChatOpenAI(
                model=settings.SUMOPOD_CHAT_MODEL,
                api_key=settings.SUMOPOD_API_KEY,
                base_url=settings.SUMOPOD_BASE_URL,
                temperature=0.0,
            )
        else:
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
