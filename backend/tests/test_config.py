"""Verifies the Settings class declares every Phase 0 env var with the right
default behavior. We monkeypatch env so the test never reads the real .env."""
import importlib
import pytest


@pytest.fixture(autouse=True)
def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "secret")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    monkeypatch.setenv("PINECONE_API_KEY", "pinecone-key")


def _reload_settings():
    from app.core import config
    importlib.reload(config)
    # Settings(env_file=".env") also reads the real .env file on disk, which
    # in this dev container is fully populated — bypassing it here so fields
    # this test doesn't monkeypatch fall through to the code's own default
    # instead of silently picking up the real dev value.
    return config.Settings(_env_file=None)


def test_settings_has_supabase_service_role_key() -> None:
    s = _reload_settings()
    assert s.SUPABASE_SERVICE_ROLE_KEY == "service-role"


def test_settings_has_google_api_key() -> None:
    s = _reload_settings()
    assert s.GOOGLE_API_KEY == "google-key"


def test_settings_has_gemini_model_defaults() -> None:
    s = _reload_settings()
    assert s.GEMINI_CHAT_MODEL == "gemini-3.1-flash-lite"


def test_settings_has_pinecone_config() -> None:
    s = _reload_settings()
    assert s.PINECONE_API_KEY == "pinecone-key"
    assert s.PINECONE_INDEX_NAME == "astalink-regulations"


def test_settings_does_not_have_openai_api_key() -> None:
    s = _reload_settings()
    assert not hasattr(s, "OPENAI_API_KEY"), \
        "OPENAI_API_KEY must be removed from Settings in Phase 0"
