"""Lazy singleton Gemini chat and embedding clients.

Construction is deferred to first use so the backend can boot even when
GOOGLE_API_KEY is unset (e.g. during partial-config dev work). Failures
surface only when a caller actually invokes the model."""
from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.core.config import settings

_chat_model: ChatGoogleGenerativeAI | None = None
_embedding_model: GoogleGenerativeAIEmbeddings | None = None


def get_chat_model() -> ChatGoogleGenerativeAI:
    global _chat_model
    if _chat_model is None:
        _chat_model = ChatGoogleGenerativeAI(
            model=settings.GEMINI_CHAT_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0,
        )
    return _chat_model


def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    global _embedding_model
    if _embedding_model is None:
        # langchain-google-genai expects "models/<id>" prefix for embedding models
        _embedding_model = GoogleGenerativeAIEmbeddings(
            model=f"models/{settings.GEMINI_EMBEDDING_MODEL}",
            google_api_key=settings.GOOGLE_API_KEY,
        )
    return _embedding_model
