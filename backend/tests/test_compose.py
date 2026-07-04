"""Verifies docker-compose.yml passes the right env vars to the backend
and includes a Prometheus service for Phase 8 observability work.

Reads a repo-root file that lives outside the backend Docker build context
(only ./backend is COPY'd into the image), so it skips — rather than fail —
when run inside that container instead of against a full checkout."""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"

pytestmark = pytest.mark.skipif(
    not COMPOSE_FILE.exists(),
    reason="repo root docker-compose.yml not present in this build context (e.g. backend-only Docker image)",
)


def test_compose_passes_gemini_and_pinecone_env() -> None:
    compose = COMPOSE_FILE.read_text()

    for key in (
        "GOOGLE_API_KEY",
        "GEMINI_CHAT_MODEL",
        "PINECONE_API_KEY",
        "PINECONE_INDEX_NAME",
        "SUPABASE_SERVICE_ROLE_KEY",
    ):
        assert key in compose, f"docker-compose.yml missing {key}"


def test_compose_does_not_pass_openai_env() -> None:
    compose = COMPOSE_FILE.read_text()
    assert "OPENAI_API_KEY" not in compose


def test_compose_has_prometheus_service() -> None:
    compose = COMPOSE_FILE.read_text()
    assert "prometheus:" in compose
    assert "9090" in compose  # default Prometheus UI port
