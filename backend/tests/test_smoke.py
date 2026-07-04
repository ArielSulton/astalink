"""End-to-end Phase 0 smoke test.

This test is deliberately broad — its job is to catch regressions early.
If any of the new Phase 0 modules can't be imported or the FastAPI app
can't be constructed, this test fails loudly."""
import importlib

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


def test_all_phase0_modules_import() -> None:
    """A single broken import here means the backend can't boot."""
    import app.core.config  # noqa: F401
    import app.core.gemini  # noqa: F401
    import app.core.pinecone  # noqa: F401
    import app.core.supabase_admin  # noqa: F401
    import app.agents.state  # noqa: F401
    import app.agents.chat_agent  # noqa: F401
    import app.main  # noqa: F401


def test_settings_loads_with_minimal_env() -> None:
    from app.core import config as config_module
    importlib.reload(config_module)
    s = config_module.Settings()
    assert s.SUPABASE_URL == "https://test.supabase.co"
    assert s.GOOGLE_API_KEY == "d"
    assert s.PINECONE_API_KEY == "e"


def test_clients_construct_without_error() -> None:
    """Each client must construct successfully when invoked.

    We patch the underlying SDK constructors so we don't make real
    network calls — the assertion is that the wiring works end-to-end."""
    # Reload config so settings reflects the monkeypatched env
    from app.core import config as config_module
    importlib.reload(config_module)
    from app.core import gemini as g
    from app.core import pinecone as p
    from app.core import supabase_admin as sa
    importlib.reload(g)
    importlib.reload(p)
    importlib.reload(sa)

    g._chat_model = None
    p._client = None
    p._index = None
    sa._client = None

    with patch("app.core.gemini.ChatGoogleGenerativeAI", return_value=MagicMock()), \
         patch("app.core.pinecone.Pinecone", return_value=MagicMock()), \
         patch("app.core.supabase_admin.create_client", return_value=MagicMock()):

        assert g.get_chat_model() is not None
        assert p.get_pinecone_client() is not None
        assert p.get_index() is not None
        assert sa.get_admin_client() is not None


def test_fastapi_app_constructs_and_health_works() -> None:
    """If the app can't construct, /health is unreachable. Catches
    regressions in main.py wiring."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_new_state_propagates_audit_id_through_messages() -> None:
    """Sanity check that a node-style update of AgentState preserves audit_id."""
    from app.agents.state import new_state

    s = new_state()
    audit_id = s["audit_id"]

    # Simulate a node returning a partial update
    update = {"intent": "ALLOCATE_STOCKS", "entities": {"amount": 10_000_000}}
    s.update(update)

    assert s["audit_id"] == audit_id
    assert s["intent"] == "ALLOCATE_STOCKS"
    assert s["revision_count"] == 0  # untouched
