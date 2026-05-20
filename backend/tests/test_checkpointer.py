from unittest.mock import MagicMock, patch


def test_get_checkpointer_uses_postgres_url(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "a")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "b")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "c")
    monkeypatch.setenv("GOOGLE_API_KEY", "d")
    monkeypatch.setenv("PINECONE_API_KEY", "e")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://u:p@h:5432/postgres")

    import importlib
    from app.core import config as config_module
    importlib.reload(config_module)
    import app.core.checkpointer as cp
    importlib.reload(cp)
    cp._saver = None

    fake = MagicMock()
    with patch("app.core.checkpointer.PostgresSaver.from_conn_string", return_value=fake) as f:
        first = cp.get_checkpointer()
        second = cp.get_checkpointer()

    assert first is second
    f.assert_called_once_with("postgresql://u:p@h:5432/postgres")


def test_get_checkpointer_falls_back_to_memory_when_no_db_url(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "a")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "b")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "c")
    monkeypatch.setenv("GOOGLE_API_KEY", "d")
    monkeypatch.setenv("PINECONE_API_KEY", "e")
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    import importlib
    import app.core.config
    importlib.reload(app.core.config)
    import app.core.checkpointer as cp
    importlib.reload(cp)
    cp._saver = None

    saver = cp.get_checkpointer()
    from langgraph.checkpoint.memory import MemorySaver
    assert isinstance(saver, MemorySaver)
