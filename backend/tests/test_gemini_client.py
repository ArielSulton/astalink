"""Verifies Gemini singletons are lazy and cached.

We don't instantiate real Gemini clients in tests — we patch the constructors
to verify the wiring (lazy init, caching, correct model strings)."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "a")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "b")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "c")
    monkeypatch.setenv("GOOGLE_API_KEY", "d")
    monkeypatch.setenv("PINECONE_API_KEY", "e")


def test_get_chat_model_is_lazy_and_cached() -> None:
    """First call constructs; second call returns cached instance."""
    # Reset module cache before the test
    import app.core.gemini as g
    g._chat_model = None

    fake_instance = MagicMock(name="ChatGoogleGenerativeAI-instance")
    with patch("app.core.gemini.ChatGoogleGenerativeAI", return_value=fake_instance) as ctor:
        first = g.get_chat_model()
        second = g.get_chat_model()

    assert first is second, "should return cached singleton"
    assert ctor.call_count == 1, "constructor must be called exactly once"

    # Verify model string and api_key were passed
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
