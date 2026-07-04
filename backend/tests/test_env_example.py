"""Verifies .env.example documents every env var the backend reads.

Missing keys are caught here at test time instead of at boot time. These
tests read repo-root files that live outside the backend Docker build
context (only ./backend is COPY'd into the image), so they skip — rather
than fail — when run inside that container instead of against a full
checkout."""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
ENV_EXAMPLE = REPO_ROOT / ".env.example"

pytestmark = pytest.mark.skipif(
    not ENV_EXAMPLE.exists(),
    reason="repo root .env.example not present in this build context (e.g. backend-only Docker image)",
)


def test_env_example_has_required_phase0_keys() -> None:
    env = ENV_EXAMPLE.read_text()

    required_keys = [
        # Supabase
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_JWT_SECRET",
        "SUPABASE_SERVICE_ROLE_KEY",  # NEW: needed for admin client
        # Gemini
        "GOOGLE_API_KEY",
        "GEMINI_CHAT_MODEL",
        # Pinecone
        "PINECONE_API_KEY",
        "PINECONE_INDEX_NAME",
        # Backend
        "BACKEND_PORT",
        "BACKEND_CORS_ORIGINS",
        # Frontend
        "FRONTEND_PORT",
        "NEXT_PUBLIC_SUPABASE_URL",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "NEXT_PUBLIC_BACKEND_URL",
        # Production
        "PROD_DOMAIN",
    ]

    for key in required_keys:
        assert f"{key}=" in env, f".env.example missing {key}"


def test_env_example_does_not_reference_openai() -> None:
    env = ENV_EXAMPLE.read_text()
    assert "OPENAI_API_KEY" not in env, "OpenAI key must be removed in Phase 0"
