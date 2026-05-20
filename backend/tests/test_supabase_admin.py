"""Verifies the service-role Supabase client is lazy + cached, uses the
service-role key (NOT the anon key), and is constructed against the project URL."""
import importlib

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def _reload_config_with_test_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "secret")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "g")
    monkeypatch.setenv("PINECONE_API_KEY", "p")

    from app.core import config as config_module
    importlib.reload(config_module)
    from app.core import supabase_admin as sa_module
    importlib.reload(sa_module)
    yield


def test_get_admin_client_uses_service_role_key() -> None:
    import app.core.supabase_admin as sa
    sa._client = None

    fake_instance = MagicMock(name="supabase-Client")
    with patch("app.core.supabase_admin.create_client", return_value=fake_instance) as ctor:
        first = sa.get_admin_client()
        second = sa.get_admin_client()

    assert first is second
    assert ctor.call_count == 1
    args = ctor.call_args.args
    assert args[0] == "https://test.supabase.co"
    assert args[1] == "service-role-key", "must use service-role key, not anon"
