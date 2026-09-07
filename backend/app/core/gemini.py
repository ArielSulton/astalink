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
_vision_model: BaseChatModel | None = None


def get_chat_model() -> BaseChatModel:
    global _chat_model
    if _chat_model is None:
        if settings.LLM_PROVIDER == "sumopod":
            # SumoPod is an OpenAI-compatible proxy (e.g. fronting DeepSeek) —
            # same client class OpenAI itself uses, just pointed elsewhere.
            #
            # thinking: disabled — per DeepSeek's own API docs
            # (api-docs.deepseek.com/guides/thinking_mode), a DeepSeek model
            # left in its default "thinking" mode rejects a *forced*
            # tool_choice ("Thinking mode does not support this tool_choice"),
            # which breaks with_structured_output(method="function_calling")
            # everywhere it's used (confirmed live: intent classification).
            # Disabling thinking mode via extra_body — also per those same
            # docs — unblocks it. (method="json_schema" still 400s regardless
            # of this setting — that's SumoPod/litellm not implementing
            # OpenAI's newer strict response_format at all, a proxy-level
            # gap, not a thinking-mode one.)
            _chat_model = ChatOpenAI(
                model=settings.SUMOPOD_CHAT_MODEL,
                api_key=settings.SUMOPOD_API_KEY,
                base_url=settings.SUMOPOD_BASE_URL,
                temperature=0.0,
                extra_body={"thinking": {"type": "disabled"}},
            )
        else:
            _chat_model = ChatGoogleGenerativeAI(
                model=settings.GEMINI_CHAT_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.0,
            )
    return _chat_model


def get_vision_model() -> BaseChatModel:
    """Vision/OCR chat client — Gemini or SumoPod, switchable via
    settings.VISION_PROVIDER. Deliberately separate from LLM_PROVIDER (text
    chat) so the two can be pointed at different providers independently.

    Historically this was hardcoded to Gemini because SumoPod's default
    DeepSeek proxy model doesn't accept multimodal (image/audio) input.
    SumoPod now also exposes a vision-capable model
    (SUMOPOD_VISION_MODEL, e.g. deepseek-v4-flash-vision-exp) — set
    VISION_PROVIDER=sumopod to route photo/voice extraction there instead.
    Gemini stays the default and its code path is untouched, so reverting is
    just flipping VISION_PROVIDER back."""
    global _vision_model
    if _vision_model is None:
        if settings.VISION_PROVIDER == "sumopod":
            _vision_model = ChatOpenAI(
                model=settings.SUMOPOD_VISION_MODEL,
                api_key=settings.SUMOPOD_API_KEY,
                base_url=settings.SUMOPOD_BASE_URL,
                temperature=0.0,
                extra_body={"thinking": {"type": "disabled"}},
            )
        else:
            _vision_model = ChatGoogleGenerativeAI(
                model=settings.GEMINI_CHAT_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.0,
            )
    return _vision_model


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
