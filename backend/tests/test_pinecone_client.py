"""Verifies the Pinecone client and index handle are lazy + cached."""
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
    monkeypatch.setenv("PINECONE_API_KEY", "pc-key")

    from app.core import config as config_module
    importlib.reload(config_module)
    from app.core import pinecone as pinecone_module
    importlib.reload(pinecone_module)
    yield


def test_get_pinecone_client_is_lazy_and_cached() -> None:
    import app.core.pinecone as p
    p._client = None

    fake = MagicMock(name="Pinecone-instance")
    with patch("app.core.pinecone.Pinecone", return_value=fake) as ctor:
        first = p.get_pinecone_client()
        second = p.get_pinecone_client()

    assert first is second
    assert ctor.call_count == 1
    assert ctor.call_args.kwargs["api_key"] == "pc-key"


def test_get_index_returns_handle_for_configured_index() -> None:
    import app.core.pinecone as p
    p._client = None
    p._index = None

    fake_index = MagicMock(name="Index-instance")
    fake_client = MagicMock()
    fake_client.Index.return_value = fake_index

    with patch("app.core.pinecone.Pinecone", return_value=fake_client):
        idx = p.get_index()
        idx2 = p.get_index()

    assert idx is fake_index
    assert idx is idx2
    fake_client.Index.assert_called_once_with("astalink-regulations")
