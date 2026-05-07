"""Verifies docker-compose.yml passes the right env vars to the backend
and includes a Prometheus service for Phase 8 observability work."""
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def test_compose_passes_gemini_and_pinecone_env() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text()

    for key in (
        "GOOGLE_API_KEY",
        "GEMINI_CHAT_MODEL",
        "GEMINI_EMBEDDING_MODEL",
        "PINECONE_API_KEY",
        "PINECONE_INDEX_NAME",
        "SUPABASE_SERVICE_ROLE_KEY",
    ):
        assert key in compose, f"docker-compose.yml missing {key}"


def test_compose_does_not_pass_openai_env() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "OPENAI_API_KEY" not in compose


def test_compose_has_prometheus_service() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "prometheus:" in compose
    assert "9090" in compose  # default Prometheus UI port
