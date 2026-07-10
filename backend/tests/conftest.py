import pytest
from fastapi.testclient import TestClient

# Settings() reads os.environ directly, and in this dev container every
# backend env var is already set for real (docker-compose passes the whole
# .env through). A test that doesn't explicitly monkeypatch one of these
# falls back to that real value instead of the class default it means to
# exercise. Clearing them first (before each test file's own env fixture
# runs) makes that fixture authoritative regardless of the ambient shell.
_OPTIONAL_SETTINGS_ENV_VARS = [
    "GOOGLE_API_KEY",
    "GEMINI_CHAT_MODEL",
    "PINECONE_API_KEY",
    "PINECONE_INDEX_NAME",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_DB_URL",
    "NEWS_API_KEY",
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "APP_BASE_URL",
    "BACKEND_CORS_ORIGINS",
    "DEBUG",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
    "ADMIN_EMAILS",
]


@pytest.fixture(autouse=True)
def _isolate_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _OPTIONAL_SETTINGS_ENV_VARS:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def client() -> TestClient:
    # Deferred import: keeps pytest collection cheap and avoids triggering
    # heavy graph compilation for tests that only need a few unit-level imports.
    from app.main import app
    return TestClient(app)
