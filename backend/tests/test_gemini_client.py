"""Verifies Gemini singletons are lazy and cached.

We don't instantiate real Gemini clients in tests — we patch the constructors
to verify the wiring (lazy init, caching, correct model strings).

We reload `app.core.config` AFTER setting env so the Settings singleton
reflects monkeypatched values; otherwise the singleton would carry stale
values from the real .env loaded at conftest import time."""
import importlib

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def _reload_config_with_test_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "a")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "b")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "c")
    monkeypatch.setenv("GOOGLE_API_KEY", "d")
    monkeypatch.setenv("PINECONE_API_KEY", "e")

    # Reload config so Settings() picks up the monkeypatched env, then reload
    # gemini so its module-level `from app.core.config import settings` rebinds
    # to the fresh singleton.
    from app.core import config as config_module
    importlib.reload(config_module)
    from app.core import gemini as gemini_module
    importlib.reload(gemini_module)
    yield


def test_get_chat_model_is_lazy_and_cached() -> None:
    import app.core.gemini as g
    g._chat_model = None

    fake_instance = MagicMock(name="ChatGoogleGenerativeAI-instance")
    with patch("app.core.gemini.ChatGoogleGenerativeAI", return_value=fake_instance) as ctor:
        first = g.get_chat_model()
        second = g.get_chat_model()

    assert first is second, "should return cached singleton"
    assert ctor.call_count == 1, "constructor must be called exactly once"
    kwargs = ctor.call_args.kwargs
    assert kwargs["model"] == "gemini-1.5-flash"
    assert kwargs["google_api_key"] == "d"


def test_get_embedding_model_is_lazy_and_cached() -> None:
    import app.core.gemini as g
    g._embedding_model = None

    fake_instance = MagicMock(name="GoogleGenerativeAIEmbeddings-instance")
    with patch("app.core.gemini.GoogleGenerativeAIEmbeddings", return_value=fake_instance) as ctor:
        first = g.get_embedding_model()
        second = g.get_embedding_model()

    assert first is second
    assert ctor.call_count == 1
    kwargs = ctor.call_args.kwargs
    assert kwargs["model"] == "models/text-embedding-004"
    assert kwargs["google_api_key"] == "d"
