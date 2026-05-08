# AstaLink Phase 0 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the existing OpenAI-based template scaffold to AstaLink's full backend foundation: swap LLM provider to Google Gemini, add quant + RAG + observability dependencies, create singleton clients (Gemini, Pinecone, Supabase service-role), define the shared `AgentState` TypedDict, write Supabase migrations for workspaces / audit_log / allocation_plans / transactions / pin_codes / regulation_documents with RLS, add a Prometheus container in dev, and ship smoke tests that verify every client initializes correctly. After this phase, every subsequent phase (Legal Agent, graph orchestration, HITL, etc.) can build on a stable foundation without churning shared infra.

**Architecture:** All external clients are lazy singletons (constructed on first access, cached at module level) so the backend boots even when optional API keys are missing — failures surface only when a client is actually used. The `AgentState` TypedDict in `backend/app/agents/state.py` is the single shared contract that every node in the LangGraph pipeline (Phase 2 onward) imports. Supabase tables are created via SQL migration files in `backend/migrations/` and applied manually through Supabase Studio (the team's chosen workflow); RLS policies are written defensively (deny-by-default with explicit allow rules per workspace).

**Tech Stack:** Python 3.12, uv (package manager), FastAPI, langchain-google-genai (Gemini chat + embeddings), pinecone (v5 SDK), rank-bm25, supabase-py, scipy, numpy, cvxpy, TA-Lib (with libta-lib system dependency), yfinance, pandas, prometheus-fastapi-instrumentator, deepeval, pypdf. Docker Compose for dev; Prometheus container added.

---

## File Structure

Files this phase creates or modifies. Other Phase N+ files are NOT touched here.

```
astalink/
├── backend/
│   ├── pyproject.toml                           # MODIFY: swap langchain-openai → langchain-google-genai, add quant/RAG/observability deps
│   ├── Dockerfile.dev                           # MODIFY: install TA-Lib system library
│   ├── Dockerfile.prod                          # MODIFY: install TA-Lib system library
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py                        # MODIFY: drop OPENAI_API_KEY, add GOOGLE_API_KEY + PINECONE_* + SUPABASE_SERVICE_ROLE_KEY
│   │   │   ├── gemini.py                        # CREATE: lazy singleton chat + embedding clients
│   │   │   ├── pinecone.py                      # CREATE: lazy singleton Pinecone index handle
│   │   │   └── supabase_admin.py                # CREATE: service-role Supabase client
│   │   └── agents/
│   │       ├── state.py                         # CREATE: AgentState TypedDict (shared contract)
│   │       └── chat_agent.py                    # MODIFY: use Gemini singleton instead of inline ChatOpenAI
│   ├── migrations/
│   │   ├── 0001_workspaces.sql                  # CREATE
│   │   ├── 0002_audit_log.sql                   # CREATE
│   │   ├── 0003_allocation_plans.sql            # CREATE
│   │   ├── 0004_transactions.sql                # CREATE
│   │   ├── 0005_pin_codes.sql                   # CREATE
│   │   ├── 0006_regulation_documents.sql        # CREATE
│   │   ├── 0007_rls_policies.sql                # CREATE
│   │   └── README.md                            # CREATE: how to apply migrations
│   └── tests/
│       ├── test_config.py                       # CREATE: settings load with new fields
│       ├── test_gemini_client.py                # CREATE: lazy init + cached singleton behavior
│       ├── test_pinecone_client.py              # CREATE: lazy init + cached singleton behavior
│       ├── test_supabase_admin.py               # CREATE: service-role client init
│       ├── test_state.py                        # CREATE: AgentState construction + field defaults
│       ├── test_chat.py                         # MODIFY: mock Gemini instead of OpenAI
│       ├── test_migrations.py                   # CREATE: assert SQL files exist with expected DDL
│       └── test_smoke.py                        # CREATE: end-to-end import + boot check for all new modules
├── prometheus/
│   └── prometheus.yml                           # CREATE: scrape backend /metrics
├── docker-compose.yml                           # MODIFY: drop OPENAI_API_KEY, add GOOGLE_API_KEY + PINECONE_* + prometheus service
└── .env.example                                 # MODIFY: drop OpenAI, add Gemini + Pinecone + service-role + Prometheus
```

---

## Task Group A — Dependency Migration

This group updates `pyproject.toml`, the env files, the Docker images, and the docker-compose definitions. No application code changes yet — those happen in Group B onward and depend on the new deps being available.

### Task A1: Update pyproject.toml — swap LLM provider, add new dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Write a test that asserts the new dependencies are declared**

Create `backend/tests/test_dependencies.py`:

```python
"""Verifies pyproject.toml declares the AstaLink Phase 0 dependencies.

This is a structural test — it parses pyproject.toml, not the lockfile, so it
catches missing/obsolete declarations even before `uv sync` is run.
"""
from pathlib import Path
import tomllib


def test_pyproject_declares_phase0_dependencies() -> None:
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text())
    deps = data["project"]["dependencies"]
    deps_str = " ".join(deps).lower()

    # LLM swap
    assert "langchain-google-genai" in deps_str, "must use Gemini, not OpenAI"
    assert "langchain-openai" not in deps_str, "OpenAI dep must be removed"

    # RAG stack
    assert "pinecone" in deps_str
    assert "rank-bm25" in deps_str
    assert "langchain-pinecone" in deps_str

    # Quantitative libs
    for lib in ("scipy", "numpy", "cvxpy", "yfinance", "pandas"):
        assert lib in deps_str, f"missing {lib}"

    # Observability + quality
    assert "prometheus-fastapi-instrumentator" in deps_str
    assert "deepeval" in deps_str

    # PDF ingestion (used by Phase 1 but added here so deps are stable)
    assert "pypdf" in deps_str
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_dependencies.py -v`
Expected: FAIL with `AssertionError: must use Gemini, not OpenAI` (langchain-openai still present, langchain-google-genai missing).

- [ ] **Step 3: Update pyproject.toml**

Replace the contents of `backend/pyproject.toml` with:

```toml
[project]
name = "astalink-backend"
version = "0.1.0"
description = "AstaLink AI-CIO backend (FastAPI + LangGraph + Gemini + RAG)"
requires-python = ">=3.12"
dependencies = [
    # Web framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.8.0",
    "pydantic-settings>=2.4.0",
    "python-multipart>=0.0.9",
    "python-jose[cryptography]>=3.3.0",
    "httpx>=0.27.0",

    # AI orchestration
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
    "langchain-google-genai>=2.0.0",

    # RAG
    "pinecone>=5.0.0",
    "langchain-pinecone>=0.2.0",
    "rank-bm25>=0.2.2",
    "pypdf>=4.0.0",

    # Database
    "supabase>=2.7.0",

    # Quantitative
    "scipy>=1.13.0",
    "numpy>=1.26.0",
    "cvxpy>=1.5.0",
    "yfinance>=0.2.40",
    "pandas>=2.2.0",
    # Note: TA-Lib is intentionally NOT listed here — the Python wrapper requires
    # the libta-lib C library. It is installed via `pip install ta-lib` in the
    # Dockerfile after apt-get installing the system lib. Adding it to
    # pyproject.toml would break `uv sync` on machines without libta-lib.

    # Observability + quality
    "prometheus-fastapi-instrumentator>=7.0.0",
    "deepeval>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.hatch.build.targets.wheel]
packages = ["app"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 4: Sync the lockfile**

Run: `cd backend && uv sync --extra dev`
Expected: dependencies resolve and install. If a package fails to resolve, fix the version constraint and retry. Do NOT commit a broken lockfile.

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_dependencies.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/tests/test_dependencies.py
git commit -m "feat(deps): swap OpenAI for Gemini, add RAG/quant/observability deps for AstaLink Phase 0"
```

---

### Task A2: Update Dockerfile.dev to install TA-Lib system library

**Files:**
- Modify: `backend/Dockerfile.dev`

TA-Lib's Python wrapper (`pip install ta-lib`) requires the C library `libta-lib0` and headers. On `python:3.12-slim` we install it via apt + compile from source, since Debian's libta-lib package can be outdated.

- [ ] **Step 1: Write a test that asserts Dockerfile.dev installs ta-lib**

Create `backend/tests/test_dockerfile.py`:

```python
"""Verifies Dockerfiles install the TA-Lib C library.

Without it, `pip install ta-lib` fails inside the container, breaking Phase 3.
"""
from pathlib import Path


def test_dockerfile_dev_installs_ta_lib() -> None:
    df = (Path(__file__).parent.parent / "Dockerfile.dev").read_text()
    assert "ta-lib" in df.lower(), "Dockerfile.dev must install TA-Lib"
    # Must run pip install ta-lib (the Python wrapper) after the C lib is built
    assert "pip install ta-lib" in df.lower() or "uv pip install ta-lib" in df.lower(), \
        "Dockerfile.dev must install the ta-lib Python wrapper"


def test_dockerfile_prod_installs_ta_lib() -> None:
    df = (Path(__file__).parent.parent / "Dockerfile.prod").read_text()
    assert "ta-lib" in df.lower(), "Dockerfile.prod must install TA-Lib"
    assert "pip install ta-lib" in df.lower() or "uv pip install ta-lib" in df.lower(), \
        "Dockerfile.prod must install the ta-lib Python wrapper"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_dockerfile.py -v`
Expected: FAIL — neither Dockerfile mentions ta-lib yet.

- [ ] **Step 3: Update backend/Dockerfile.dev**

Replace contents with:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install TA-Lib C library (required by the ta-lib Python wrapper).
# We compile from source because Debian's libta-lib0 package lags upstream.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        wget \
        ca-certificates \
    && wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && cd .. \
    && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz \
    && apt-get purge -y --auto-remove wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Install ta-lib Python wrapper separately — it needs the C lib at /usr.
RUN uv pip install ta-lib

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 4: Run the dev-Dockerfile test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_dockerfile.py::test_dockerfile_dev_installs_ta_lib -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile.dev backend/tests/test_dockerfile.py
git commit -m "feat(docker): install TA-Lib C library in Dockerfile.dev"
```

---

### Task A3: Update Dockerfile.prod to install TA-Lib system library

**Files:**
- Modify: `backend/Dockerfile.prod`

- [ ] **Step 1: Run the prod-Dockerfile test to confirm it currently fails**

Run: `cd backend && uv run python -m pytest tests/test_dockerfile.py::test_dockerfile_prod_installs_ta_lib -v`
Expected: FAIL.

- [ ] **Step 2: Update backend/Dockerfile.prod**

Replace contents with:

```dockerfile
# backend/Dockerfile.prod
FROM python:3.12-slim AS builder

WORKDIR /app

# Build TA-Lib C library
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        wget \
        ca-certificates \
    && wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && cd .. \
    && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

RUN pip install uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev
RUN uv pip install ta-lib

COPY app/ ./app/

# Final stage — copy from builder, drop build tools
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy TA-Lib C library + Python venv + app code from builder
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
COPY --from=builder /usr/include/ta-lib /usr/include/ta-lib
COPY --from=builder /app /app

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

- [ ] **Step 3: Run the prod-Dockerfile test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_dockerfile.py -v`
Expected: PASS for both dev and prod.

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile.prod
git commit -m "feat(docker): install TA-Lib C library in Dockerfile.prod with multi-stage build"
```

---

### Task A4: Update .env.example — drop OpenAI, add Gemini / Pinecone / service-role / Prometheus keys

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Write a test that asserts .env.example declares the new keys**

Create `backend/tests/test_env_example.py`:

```python
"""Verifies .env.example documents every env var the backend reads.

Missing keys are caught here at test time instead of at boot time."""
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def test_env_example_has_required_phase0_keys() -> None:
    env = (REPO_ROOT / ".env.example").read_text()

    required_keys = [
        # Supabase
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_JWT_SECRET",
        "SUPABASE_SERVICE_ROLE_KEY",  # NEW: needed for admin client
        # Gemini
        "GOOGLE_API_KEY",
        "GEMINI_CHAT_MODEL",
        "GEMINI_EMBEDDING_MODEL",
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
    env = (REPO_ROOT / ".env.example").read_text()
    assert "OPENAI_API_KEY" not in env, "OpenAI key must be removed in Phase 0"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_env_example.py -v`
Expected: FAIL — .env.example still has OPENAI_API_KEY and is missing the new keys.

- [ ] **Step 3: Replace .env.example contents**

Replace `.env.example` (at repo root) with:

```bash
# Supabase (shared between frontend and backend)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
# Service-role key — backend ONLY, never expose to frontend.
# Used for admin writes that bypass RLS (audit_log, regulation_documents).
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Google Gemini (for LangGraph agents and RAG embeddings)
GOOGLE_API_KEY=your-google-api-key
GEMINI_CHAT_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004

# Pinecone (vector DB for Legal Agent RAG)
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=astalink-regulations

# Backend
BACKEND_PORT=8000
BACKEND_CORS_ORIGINS=http://localhost:3000

# Frontend
FRONTEND_PORT=3000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000  # Dev only; prod uses /api via reverse proxy

# Production
PROD_DOMAIN=https://yourdomain.com
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_env_example.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .env.example backend/tests/test_env_example.py
git commit -m "feat(env): document Gemini, Pinecone, and Supabase service-role keys in .env.example"
```

---

### Task A5: Update docker-compose.yml — swap env vars, add Prometheus service

**Files:**
- Modify: `docker-compose.yml`
- Create: `prometheus/prometheus.yml`

- [ ] **Step 1: Write a test asserting docker-compose.yml has the new env vars and prometheus service**

Create `backend/tests/test_compose.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_compose.py -v`
Expected: FAIL on all three.

- [ ] **Step 3: Create prometheus/prometheus.yml**

Create the file at repo root: `prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'astalink-backend'
    metrics_path: /metrics
    static_configs:
      - targets: ['backend:8000']
        labels:
          service: backend
          env: dev
```

- [ ] **Step 4: Replace docker-compose.yml**

Replace contents with:

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "${FRONTEND_PORT:-3000}:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    environment:
      - NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}
      - NEXT_PUBLIC_BACKEND_URL=http://localhost:${BACKEND_PORT:-8000}
    depends_on:
      - backend

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    volumes:
      - ./backend:/app
    environment:
      # Supabase
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      # Gemini
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - GEMINI_CHAT_MODEL=${GEMINI_CHAT_MODEL:-gemini-1.5-flash}
      - GEMINI_EMBEDDING_MODEL=${GEMINI_EMBEDDING_MODEL:-text-embedding-004}
      # Pinecone
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_INDEX_NAME=${PINECONE_INDEX_NAME:-astalink-regulations}
      # Backend
      - BACKEND_CORS_ORIGINS=["http://localhost:${FRONTEND_PORT:-3000}"]
      - DEBUG=true

  prometheus:
    image: prom/prometheus:v2.55.0
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    depends_on:
      - backend

volumes:
  prometheus_data:
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_compose.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml prometheus/prometheus.yml backend/tests/test_compose.py
git commit -m "feat(compose): wire Gemini/Pinecone env, add Prometheus service for dev observability"
```

---

## Task Group B — Configuration

### Task B1: Update Settings — drop OPENAI_API_KEY, add new fields

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_config.py`:

```python
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
    return config.settings


def test_settings_has_supabase_service_role_key() -> None:
    s = _reload_settings()
    assert s.SUPABASE_SERVICE_ROLE_KEY == "service-role"


def test_settings_has_google_api_key() -> None:
    s = _reload_settings()
    assert s.GOOGLE_API_KEY == "google-key"


def test_settings_has_gemini_model_defaults() -> None:
    s = _reload_settings()
    assert s.GEMINI_CHAT_MODEL == "gemini-1.5-flash"
    assert s.GEMINI_EMBEDDING_MODEL == "text-embedding-004"


def test_settings_has_pinecone_config() -> None:
    s = _reload_settings()
    assert s.PINECONE_API_KEY == "pinecone-key"
    assert s.PINECONE_INDEX_NAME == "astalink-regulations"


def test_settings_does_not_have_openai_api_key() -> None:
    s = _reload_settings()
    assert not hasattr(s, "OPENAI_API_KEY"), \
        "OPENAI_API_KEY must be removed from Settings in Phase 0"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_config.py -v`
Expected: FAIL — Settings still has OPENAI_API_KEY and lacks the new fields.

- [ ] **Step 3: Replace backend/app/core/config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "AstaLink Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Supabase (anon + JWT for user-scoped requests; service-role for admin writes)
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Google Gemini
    GOOGLE_API_KEY: str
    GEMINI_CHAT_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"

    # Pinecone
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "astalink-regulations"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]


settings = Settings()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/tests/test_config.py
git commit -m "feat(config): drop OPENAI_API_KEY, add Gemini/Pinecone/Supabase service-role settings"
```

---

## Task Group C — Singleton Clients

Lazy singletons: built on first access, cached at module level. This means the app boots even when an external API key is missing — failures surface only when a client is actually invoked.

### Task C1: Gemini chat + embedding singletons

**Files:**
- Create: `backend/app/core/gemini.py`
- Create: `backend/tests/test_gemini_client.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_gemini_client.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_gemini_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.gemini'`.

- [ ] **Step 3: Create backend/app/core/gemini.py**

```python
"""Lazy singleton Gemini chat and embedding clients.

Construction is deferred to first use so the backend can boot even when
GOOGLE_API_KEY is unset (e.g. during partial-config dev work). Failures
surface only when a caller actually invokes the model."""
from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.core.config import settings

_chat_model: ChatGoogleGenerativeAI | None = None
_embedding_model: GoogleGenerativeAIEmbeddings | None = None


def get_chat_model() -> ChatGoogleGenerativeAI:
    global _chat_model
    if _chat_model is None:
        _chat_model = ChatGoogleGenerativeAI(
            model=settings.GEMINI_CHAT_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0,
        )
    return _chat_model


def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    global _embedding_model
    if _embedding_model is None:
        # langchain-google-genai expects "models/<id>" prefix for embedding models
        _embedding_model = GoogleGenerativeAIEmbeddings(
            model=f"models/{settings.GEMINI_EMBEDDING_MODEL}",
            google_api_key=settings.GOOGLE_API_KEY,
        )
    return _embedding_model
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_gemini_client.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/gemini.py backend/tests/test_gemini_client.py
git commit -m "feat(core): add lazy Gemini chat + embedding singletons"
```

---

### Task C2: Pinecone index handle singleton

**Files:**
- Create: `backend/app/core/pinecone.py`
- Create: `backend/tests/test_pinecone_client.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_pinecone_client.py`:

```python
"""Verifies the Pinecone client and index handle are lazy + cached."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "a")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "b")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "c")
    monkeypatch.setenv("GOOGLE_API_KEY", "d")
    monkeypatch.setenv("PINECONE_API_KEY", "pc-key")


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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_pinecone_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.pinecone'`.

- [ ] **Step 3: Create backend/app/core/pinecone.py**

```python
"""Lazy singleton Pinecone client + index handle for AstaLink RAG (Phase 1).

The Pinecone SDK v5 separates the control-plane client (`Pinecone`) from a
data-plane handle (`client.Index(name)`). We cache both."""
from __future__ import annotations

from pinecone import Pinecone

from app.core.config import settings

_client: Pinecone | None = None
_index = None  # pinecone.Index — type omitted because the SDK doesn't export it cleanly


def get_pinecone_client() -> Pinecone:
    global _client
    if _client is None:
        _client = Pinecone(api_key=settings.PINECONE_API_KEY)
    return _client


def get_index():
    """Returns the configured index handle. Caller is responsible for ensuring
    the index has been created in the Pinecone console (one-time bootstrap)."""
    global _index
    if _index is None:
        client = get_pinecone_client()
        _index = client.Index(settings.PINECONE_INDEX_NAME)
    return _index
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_pinecone_client.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/pinecone.py backend/tests/test_pinecone_client.py
git commit -m "feat(core): add lazy Pinecone client + index handle singletons"
```

---

### Task C3: Supabase service-role admin client

**Files:**
- Create: `backend/app/core/supabase_admin.py`
- Create: `backend/tests/test_supabase_admin.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_supabase_admin.py`:

```python
"""Verifies the service-role Supabase client is lazy + cached, uses the
service-role key (NOT the anon key), and is constructed against the project URL."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "secret")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "g")
    monkeypatch.setenv("PINECONE_API_KEY", "p")


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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_supabase_admin.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create backend/app/core/supabase_admin.py**

```python
"""Lazy singleton Supabase service-role client.

Use this client ONLY for operations that legitimately need to bypass RLS
(e.g. system writes to audit_log, regulation_documents). For user-scoped
reads/writes, use the anon client + the user's JWT so RLS is enforced."""
from __future__ import annotations

from supabase import Client, create_client

from app.core.config import settings

_client: Client | None = None


def get_admin_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    return _client
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_supabase_admin.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/supabase_admin.py backend/tests/test_supabase_admin.py
git commit -m "feat(core): add lazy Supabase service-role admin client"
```

---

## Task Group D — Shared AgentState

### Task D1: Define AgentState TypedDict

**Files:**
- Create: `backend/app/agents/state.py`
- Create: `backend/tests/test_state.py`

`AgentState` is the single shared contract that every LangGraph node (Phase 2 onward) reads and writes. Defining it cleanly here means later phases don't need to renegotiate fields.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_state.py`:

```python
"""Verifies the AgentState TypedDict has the contracted shape.

LangGraph nodes will partial-update this dict; the test ensures all fields
the master plan requires are declared with sensible types and defaults."""
import uuid
from app.agents.state import AgentState, new_state, LegalStatus


def test_agentstate_has_required_keys() -> None:
    keys = AgentState.__annotations__.keys()
    expected = {
        "audit_id",
        "messages",
        "intent",
        "entities",
        "allocation_plan",
        "revision_count",
        "legal_status",
        "legal_citations",
        "user_approval",
        "transactions",
        "errors",
    }
    missing = expected - set(keys)
    assert not missing, f"AgentState missing keys: {missing}"


def test_new_state_generates_audit_id_and_zero_revisions() -> None:
    s = new_state()

    # audit_id must be a valid UUID4 string
    uuid.UUID(s["audit_id"], version=4)

    assert s["revision_count"] == 0
    assert s["messages"] == []
    assert s["legal_status"] is None
    assert s["user_approval"] is None
    assert s["allocation_plan"] is None
    assert s["entities"] == {}
    assert s["transactions"] == []
    assert s["errors"] == []


def test_legal_status_enum_values() -> None:
    assert LegalStatus.APPROVED == "approved"
    assert LegalStatus.PARTIAL == "partial"
    assert LegalStatus.REJECTED == "rejected"
    assert LegalStatus.REJECTED_AFTER_MAX_REVISIONS == "rejected_after_max_revisions"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.state'`.

- [ ] **Step 3: Create backend/app/agents/state.py**

```python
"""Shared AgentState for the AstaLink LangGraph pipeline.

Every node reads and partially updates this state. Fields that are unknown
at a given pipeline stage are typed as Optional and start as None.

The `audit_id` is generated by N1 (intent classifier) and propagated through
every downstream node and Supabase write, so a single trace can be reconstructed
from logs + audit_log table."""
from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any, TypedDict

from langchain_core.messages import BaseMessage


class LegalStatus(StrEnum):
    APPROVED = "approved"
    PARTIAL = "partial"
    REJECTED = "rejected"
    REJECTED_AFTER_MAX_REVISIONS = "rejected_after_max_revisions"


class UserApproval(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class AgentState(TypedDict, total=False):
    """Shared state across every LangGraph node.

    `total=False` so partial updates from individual nodes type-check;
    keys absent from a node's return value are left untouched by LangGraph."""

    # Trace
    audit_id: str

    # Conversation
    messages: list[BaseMessage]

    # N1 — Intent
    intent: str | None
    entities: dict[str, Any]

    # N2/N5 — Allocation
    allocation_plan: dict[str, Any] | None
    revision_count: int

    # N3 — Legal
    legal_status: LegalStatus | None
    legal_citations: list[dict[str, Any]]

    # N6 — HITL
    user_approval: UserApproval | None

    # N7 — Execution
    transactions: list[dict[str, Any]]

    # Cross-cutting
    errors: list[dict[str, Any]]


def new_state() -> AgentState:
    """Build a fresh AgentState for a new pipeline run.

    audit_id is generated here once and immutable for the lifetime of the run."""
    return AgentState(
        audit_id=str(uuid.uuid4()),
        messages=[],
        intent=None,
        entities={},
        allocation_plan=None,
        revision_count=0,
        legal_status=None,
        legal_citations=[],
        user_approval=None,
        transactions=[],
        errors=[],
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_state.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/state.py backend/tests/test_state.py
git commit -m "feat(agents): add shared AgentState TypedDict with audit_id, legal_status, revision_count"
```

---

## Task Group E — Update Existing Chat Agent to Gemini

The template's toy chat agent at `backend/app/agents/chat_agent.py` directly imports `langchain_openai`. We swap it to use the Gemini singleton from Task C1 so the existing chat endpoint keeps working post-migration. This also acts as an integration smoke test: if Gemini works for the chat endpoint, the singleton plumbing is correct.

### Task E1: Migrate chat_agent.py to use Gemini singleton

**Files:**
- Modify: `backend/app/agents/chat_agent.py`
- Modify: `backend/tests/test_chat.py`

- [ ] **Step 1: Update the existing test_chat.py to mock the Gemini singleton instead of relying on chat_graph.invoke patching only**

Replace `backend/tests/test_chat.py` contents:

```python
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage


def test_chat_endpoint_without_auth_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat/",
        json={"message": "Hello"},
    )
    assert response.status_code == 401


def test_chat_endpoint_with_mocked_auth_and_agent(client: TestClient) -> None:
    """Exercises the chat endpoint end-to-end with mocked auth + Gemini.

    The chat_node should call `app.core.gemini.get_chat_model()` and use
    the returned (mocked) model — this verifies the Gemini wiring."""
    mock_user = {"sub": str(uuid.uuid4()), "email": "test@example.com"}

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Hello from Gemini!")

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.agents.chat_agent.get_chat_model", return_value=fake_llm):

        response = client.post(
            "/api/v1/chat/",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Hello from Gemini!"
    assert "thread_id" in data
    fake_llm.invoke.assert_called_once()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_chat.py -v`
Expected: FAIL — `app.agents.chat_agent.get_chat_model` doesn't exist (chat_agent.py still imports ChatOpenAI).

- [ ] **Step 3: Replace backend/app/agents/chat_agent.py**

```python
from typing import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.core.gemini import get_chat_model


class ChatState(TypedDict):
    messages: list[BaseMessage]


def chat_node(state: ChatState) -> ChatState:
    llm = get_chat_model()
    response = llm.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}


def build_chat_graph():
    graph = StateGraph(ChatState)
    graph.add_node("chat", chat_node)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)
    return graph.compile(checkpointer=MemorySaver())


# Singleton graph instance — graph compilation is cheap; the LLM is lazy.
chat_graph = build_chat_graph()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_chat.py -v`
Expected: PASS for both tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/chat_agent.py backend/tests/test_chat.py
git commit -m "refactor(chat-agent): swap inline ChatOpenAI for the lazy Gemini singleton"
```

---

## Task Group F — Supabase Schema (Migrations)

These are SQL migration files. The team applies them manually via Supabase Studio's SQL editor (the project's chosen workflow); the test assertions only verify the SQL files exist with the expected DDL — they do NOT execute SQL or require a live Supabase connection.

For Phase 5 onward to work, these tables must actually be applied — that's a manual-step DoD item at the end of the phase.

### Task F1: Migration 0001 — workspaces table

**Files:**
- Create: `backend/migrations/0001_workspaces.sql`
- Create: `backend/tests/test_migrations.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_migrations.py`:

```python
"""Structural tests for the migration files. We assert each file exists and
contains the expected DDL keywords, but we do NOT execute SQL — the team
applies migrations manually through Supabase Studio."""
from pathlib import Path

MIG_DIR = Path(__file__).parent.parent / "migrations"


def _read(name: str) -> str:
    return (MIG_DIR / name).read_text().lower()


def test_migration_0001_workspaces_exists() -> None:
    sql = _read("0001_workspaces.sql")
    assert "create table" in sql
    assert "workspaces" in sql
    assert "owner_user_id" in sql
    assert "type" in sql
    assert "personal" in sql and "business" in sql
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py -v`
Expected: FAIL — migration file does not exist.

- [ ] **Step 3: Create backend/migrations/0001_workspaces.sql**

```sql
-- 0001_workspaces.sql
-- A workspace isolates one user's data; users may have multiple workspaces
-- (e.g. one Personal + one Business). RLS policies (0007) gate access by
-- workspace ownership.

create type workspace_type as enum ('personal', 'business');

create table if not exists public.workspaces (
    id uuid primary key default gen_random_uuid(),
    owner_user_id uuid not null references auth.users (id) on delete cascade,
    type workspace_type not null,
    name text not null,
    created_at timestamptz not null default now()
);

create index if not exists workspaces_owner_idx
    on public.workspaces (owner_user_id);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0001_workspaces_exists -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/0001_workspaces.sql backend/tests/test_migrations.py
git commit -m "feat(db): add workspaces table migration (Personal/Business isolation)"
```

---

### Task F2: Migration 0002 — audit_log table

**Files:**
- Create: `backend/migrations/0002_audit_log.sql`
- Modify: `backend/tests/test_migrations.py`

- [ ] **Step 1: Append the failing test**

Add to `backend/tests/test_migrations.py`:

```python
def test_migration_0002_audit_log_exists() -> None:
    sql = _read("0002_audit_log.sql")
    assert "create table" in sql
    assert "audit_log" in sql
    assert "audit_id" in sql
    assert "workspace_id" in sql
    assert "intent" in sql
    assert "payload" in sql
    assert "jsonb" in sql
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0002_audit_log_exists -v`
Expected: FAIL.

- [ ] **Step 3: Create backend/migrations/0002_audit_log.sql**

```sql
-- 0002_audit_log.sql
-- The audit_log is the source of truth for every pipeline run. Every node
-- (N1..N7) writes to it, keyed by audit_id. This is what makes "audit trail
-- end-to-end" enforceable.

create table if not exists public.audit_log (
    audit_id uuid primary key,
    workspace_id uuid not null references public.workspaces (id) on delete cascade,
    user_id uuid not null references auth.users (id) on delete cascade,
    intent text,
    status text not null default 'in_progress',
        -- in_progress | awaiting_approval | approved | rejected | executed | failed
    created_at timestamptz not null default now(),
    completed_at timestamptz,
    payload jsonb not null default '{}'::jsonb
);

create index if not exists audit_log_workspace_idx
    on public.audit_log (workspace_id, created_at desc);
create index if not exists audit_log_user_idx
    on public.audit_log (user_id, created_at desc);
create index if not exists audit_log_status_idx
    on public.audit_log (status);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0002_audit_log_exists -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/0002_audit_log.sql backend/tests/test_migrations.py
git commit -m "feat(db): add audit_log table migration for end-to-end pipeline tracing"
```

---

### Task F3: Migration 0003 — allocation_plans table

**Files:**
- Create: `backend/migrations/0003_allocation_plans.sql`
- Modify: `backend/tests/test_migrations.py`

- [ ] **Step 1: Append the failing test**

Add to `backend/tests/test_migrations.py`:

```python
def test_migration_0003_allocation_plans_exists() -> None:
    sql = _read("0003_allocation_plans.sql")
    assert "create table" in sql
    assert "allocation_plans" in sql
    assert "audit_id" in sql
    assert "plan_json" in sql
    assert "legal_status" in sql
    assert "revision_count" in sql
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0003_allocation_plans_exists -v`
Expected: FAIL.

- [ ] **Step 3: Create backend/migrations/0003_allocation_plans.sql**

```sql
-- 0003_allocation_plans.sql
-- Each pipeline run produces zero or more allocation plans. A plan can be
-- revised by the optimizer (N5) up to a configured cap; revision_count tracks
-- this so the graph can terminate after max revisions.

create table if not exists public.allocation_plans (
    id uuid primary key default gen_random_uuid(),
    audit_id uuid not null references public.audit_log (audit_id) on delete cascade,
    plan_json jsonb not null,
    legal_status text,
        -- approved | partial | rejected | rejected_after_max_revisions | null
    legal_citations jsonb not null default '[]'::jsonb,
    revision_count int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists allocation_plans_audit_idx
    on public.allocation_plans (audit_id, created_at desc);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0003_allocation_plans_exists -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/0003_allocation_plans.sql backend/tests/test_migrations.py
git commit -m "feat(db): add allocation_plans table migration with revision tracking"
```

---

### Task F4: Migration 0004 — transactions table

**Files:**
- Create: `backend/migrations/0004_transactions.sql`
- Modify: `backend/tests/test_migrations.py`

- [ ] **Step 1: Append the failing test**

Add to `backend/tests/test_migrations.py`:

```python
def test_migration_0004_transactions_exists() -> None:
    sql = _read("0004_transactions.sql")
    assert "create table" in sql
    assert "transactions" in sql
    assert "allocation_plan_id" in sql
    assert "broker_ref" in sql
    # Idempotency unique constraint on (audit_id, ticker, side)
    assert "unique" in sql
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0004_transactions_exists -v`
Expected: FAIL.

- [ ] **Step 3: Create backend/migrations/0004_transactions.sql**

```sql
-- 0004_transactions.sql
-- Records each broker order placed by N7. The unique constraint on
-- (audit_id, ticker, side) gives N7 idempotency: re-running the node for the
-- same plan does not double-execute.

create table if not exists public.transactions (
    id uuid primary key default gen_random_uuid(),
    allocation_plan_id uuid not null references public.allocation_plans (id) on delete cascade,
    audit_id uuid not null references public.audit_log (audit_id) on delete cascade,
    ticker text not null,
    side text not null,            -- 'buy' | 'sell'
    quantity numeric not null,
    broker_ref text,               -- broker's order id
    status text not null,          -- 'pending' | 'filled' | 'failed'
    executed_at timestamptz,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (audit_id, ticker, side)
);

create index if not exists transactions_audit_idx
    on public.transactions (audit_id);
create index if not exists transactions_plan_idx
    on public.transactions (allocation_plan_id);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0004_transactions_exists -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/0004_transactions.sql backend/tests/test_migrations.py
git commit -m "feat(db): add transactions table migration with N7 idempotency constraint"
```

---

### Task F5: Migration 0005 — pin_codes table

**Files:**
- Create: `backend/migrations/0005_pin_codes.sql`
- Modify: `backend/tests/test_migrations.py`

- [ ] **Step 1: Append the failing test**

Add to `backend/tests/test_migrations.py`:

```python
def test_migration_0005_pin_codes_exists() -> None:
    sql = _read("0005_pin_codes.sql")
    assert "create table" in sql
    assert "pin_codes" in sql
    assert "hashed_pin" in sql
    assert "salt" in sql
    assert "attempts" in sql
    assert "locked_until" in sql
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0005_pin_codes_exists -v`
Expected: FAIL.

- [ ] **Step 3: Create backend/migrations/0005_pin_codes.sql**

```sql
-- 0005_pin_codes.sql
-- PIN-based approval gate for HITL (Phase 5). The hashing algorithm
-- (Argon2) is enforced in application code, not in DDL; this table just
-- stores the hash, salt, and a lockout counter.

create table if not exists public.pin_codes (
    user_id uuid primary key references auth.users (id) on delete cascade,
    hashed_pin text not null,
    salt text not null,
    attempts int not null default 0,
    last_failed_at timestamptz,
    locked_until timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0005_pin_codes_exists -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/0005_pin_codes.sql backend/tests/test_migrations.py
git commit -m "feat(db): add pin_codes table migration for HITL approval gate"
```

---

### Task F6: Migration 0006 — regulation_documents table

**Files:**
- Create: `backend/migrations/0006_regulation_documents.sql`
- Modify: `backend/tests/test_migrations.py`

- [ ] **Step 1: Append the failing test**

Add to `backend/tests/test_migrations.py`:

```python
def test_migration_0006_regulation_documents_exists() -> None:
    sql = _read("0006_regulation_documents.sql")
    assert "create table" in sql
    assert "regulation_documents" in sql
    assert "doc_hash" in sql
    assert "indexed_at" in sql
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0006_regulation_documents_exists -v`
Expected: FAIL.

- [ ] **Step 3: Create backend/migrations/0006_regulation_documents.sql**

```sql
-- 0006_regulation_documents.sql
-- Index of regulation PDFs ingested by Phase 1's RAG pipeline. The chunks
-- themselves live in Pinecone (dense) + a serialized BM25 index file (sparse);
-- this table is the metadata catalog.

create table if not exists public.regulation_documents (
    id uuid primary key default gen_random_uuid(),
    source text not null,        -- e.g. 'OJK', 'UUPM', 'Perpajakan'
    title text not null,
    version text,
    doc_hash text not null unique,
    indexed_at timestamptz not null default now(),
    metadata jsonb not null default '{}'::jsonb
);

create index if not exists regulation_documents_source_idx
    on public.regulation_documents (source);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0006_regulation_documents_exists -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/0006_regulation_documents.sql backend/tests/test_migrations.py
git commit -m "feat(db): add regulation_documents table migration for RAG metadata catalog"
```

---

### Task F7: Migration 0007 — RLS policies

**Files:**
- Create: `backend/migrations/0007_rls_policies.sql`
- Modify: `backend/tests/test_migrations.py`

RLS is the second line of defense. The backend always filters by `workspace_id`, but RLS ensures that even if the backend has a bug, a user with a stolen anon-token cannot read another workspace's data. We enable RLS on every Phase 0 table and write deny-by-default policies that grant only the workspace owner read/write.

- [ ] **Step 1: Append the failing test**

Add to `backend/tests/test_migrations.py`:

```python
def test_migration_0007_rls_policies_exists() -> None:
    sql = _read("0007_rls_policies.sql")
    # Enable RLS on every Phase 0 table
    for table in (
        "workspaces",
        "audit_log",
        "allocation_plans",
        "transactions",
        "pin_codes",
        "regulation_documents",
    ):
        assert f"alter table public.{table} enable row level security" in sql, \
            f"RLS not enabled on {table}"

    # At least one CREATE POLICY per protected table
    assert sql.count("create policy") >= 6, "expected ≥6 policies"

    # Workspace ownership predicate
    assert "owner_user_id = auth.uid()" in sql or "auth.uid() = owner_user_id" in sql
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0007_rls_policies_exists -v`
Expected: FAIL.

- [ ] **Step 3: Create backend/migrations/0007_rls_policies.sql**

```sql
-- 0007_rls_policies.sql
-- Deny-by-default RLS on every Phase 0 table. Service-role (used by the
-- backend admin client) bypasses RLS — but the backend should still filter
-- by workspace_id in queries; RLS is the safety net, not the only check.

-- workspaces: a user can read/write only their own workspaces
alter table public.workspaces enable row level security;
create policy workspaces_select_own on public.workspaces
    for select using (owner_user_id = auth.uid());
create policy workspaces_insert_own on public.workspaces
    for insert with check (owner_user_id = auth.uid());
create policy workspaces_update_own on public.workspaces
    for update using (owner_user_id = auth.uid());
create policy workspaces_delete_own on public.workspaces
    for delete using (owner_user_id = auth.uid());

-- audit_log: a user can read only audit rows for workspaces they own.
-- Inserts come from the backend service-role client (RLS bypassed).
alter table public.audit_log enable row level security;
create policy audit_log_select_own on public.audit_log
    for select using (
        workspace_id in (
            select id from public.workspaces where owner_user_id = auth.uid()
        )
    );

-- allocation_plans: same pattern (read-only via user JWT)
alter table public.allocation_plans enable row level security;
create policy allocation_plans_select_own on public.allocation_plans
    for select using (
        audit_id in (
            select audit_id from public.audit_log
            where workspace_id in (
                select id from public.workspaces where owner_user_id = auth.uid()
            )
        )
    );

-- transactions: same pattern
alter table public.transactions enable row level security;
create policy transactions_select_own on public.transactions
    for select using (
        audit_id in (
            select audit_id from public.audit_log
            where workspace_id in (
                select id from public.workspaces where owner_user_id = auth.uid()
            )
        )
    );

-- pin_codes: a user can read/write only their own row
alter table public.pin_codes enable row level security;
create policy pin_codes_select_own on public.pin_codes
    for select using (user_id = auth.uid());
create policy pin_codes_insert_own on public.pin_codes
    for insert with check (user_id = auth.uid());
create policy pin_codes_update_own on public.pin_codes
    for update using (user_id = auth.uid());

-- regulation_documents: world-readable (regulations aren't user-scoped),
-- writes only via service-role.
alter table public.regulation_documents enable row level security;
create policy regulation_documents_select_all on public.regulation_documents
    for select using (true);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0007_rls_policies_exists -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/0007_rls_policies.sql backend/tests/test_migrations.py
git commit -m "feat(db): add RLS policies for workspace-scoped access to all Phase 0 tables"
```

---

### Task F8: Migrations README

**Files:**
- Create: `backend/migrations/README.md`

- [ ] **Step 1: Create backend/migrations/README.md**

```markdown
# AstaLink Database Migrations

Plain SQL migrations applied manually via the Supabase Studio SQL editor.

## How to apply

1. Open your Supabase project → **SQL Editor**.
2. Paste the contents of each `NNNN_*.sql` file in numerical order.
3. Run each. Verify under **Table Editor** that the new table appears with the
   expected columns and that **Enable RLS** shows green.
4. After all migrations are applied, smoke-test from the Phase 0 acceptance
   checklist (insert one workspace as the authenticated user, confirm select
   returns it; confirm a second user cannot select it).

## Why not automated?

For the hackathon timeline, manual application via Supabase Studio is the
team's chosen workflow. A future enhancement could move this to
`supabase migration` CLI or the [supabase-py migrations API], but that's out
of scope for Phase 0.

## File order

| File | Purpose |
|------|---------|
| `0001_workspaces.sql` | Workspace isolation (Personal/Business) |
| `0002_audit_log.sql` | End-to-end pipeline trace |
| `0003_allocation_plans.sql` | Per-run allocation proposals + revision count |
| `0004_transactions.sql` | Broker orders with idempotency constraint |
| `0005_pin_codes.sql` | HITL approval gate storage |
| `0006_regulation_documents.sql` | RAG metadata catalog |
| `0007_rls_policies.sql` | Deny-by-default workspace-scoped access |
```

- [ ] **Step 2: Commit**

```bash
git add backend/migrations/README.md
git commit -m "docs(db): document manual migration workflow"
```

---

## Task Group G — Smoke Test

A single end-to-end import + boot test that catches regressions across all the new modules. Whenever someone modifies any Phase 0 file, this test runs and surfaces breakage.

### Task G1: Boot smoke test

**Files:**
- Create: `backend/tests/test_smoke.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_smoke.py`:

```python
"""End-to-end Phase 0 smoke test.

This test is deliberately broad — its job is to catch regressions early.
If any of the new Phase 0 modules can't be imported or the FastAPI app
can't be constructed, this test fails loudly."""
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
    from app.core.config import Settings
    s = Settings()
    assert s.SUPABASE_URL == "https://test.supabase.co"
    assert s.GOOGLE_API_KEY == "d"
    assert s.PINECONE_API_KEY == "e"


def test_clients_construct_without_error() -> None:
    """Each client must construct successfully when invoked.

    We patch the underlying SDK constructors so we don't make real
    network calls — the assertion is that the wiring works end-to-end."""
    import app.core.gemini as g
    import app.core.pinecone as p
    import app.core.supabase_admin as sa

    g._chat_model = None
    g._embedding_model = None
    p._client = None
    p._index = None
    sa._client = None

    with patch("app.core.gemini.ChatGoogleGenerativeAI", return_value=MagicMock()), \
         patch("app.core.gemini.GoogleGenerativeAIEmbeddings", return_value=MagicMock()), \
         patch("app.core.pinecone.Pinecone", return_value=MagicMock()), \
         patch("app.core.supabase_admin.create_client", return_value=MagicMock()):

        assert g.get_chat_model() is not None
        assert g.get_embedding_model() is not None
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
```

- [ ] **Step 2: Run the test**

Run: `cd backend && uv run python -m pytest tests/test_smoke.py -v`
Expected: PASS for all five tests.

If any test fails, the failure points to a regression in the corresponding Phase 0 module — fix it before continuing.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_smoke.py
git commit -m "test(smoke): add Phase 0 end-to-end boot smoke test"
```

---

## Task Group H — Final Verification

### Task H1: Full test-suite run

- [ ] **Step 1: Run the full backend test suite**

Run: `cd backend && PYTHONPATH="" uv run python -m pytest tests/ -v`
Expected: ALL PASS. The expected test names (in any order):

```
tests/test_chat.py::test_chat_endpoint_without_auth_returns_401 PASSED
tests/test_chat.py::test_chat_endpoint_with_mocked_auth_and_agent PASSED
tests/test_compose.py::test_compose_passes_gemini_and_pinecone_env PASSED
tests/test_compose.py::test_compose_does_not_pass_openai_env PASSED
tests/test_compose.py::test_compose_has_prometheus_service PASSED
tests/test_config.py::test_settings_has_supabase_service_role_key PASSED
tests/test_config.py::test_settings_has_google_api_key PASSED
tests/test_config.py::test_settings_has_gemini_model_defaults PASSED
tests/test_config.py::test_settings_has_pinecone_config PASSED
tests/test_config.py::test_settings_does_not_have_openai_api_key PASSED
tests/test_dependencies.py::test_pyproject_declares_phase0_dependencies PASSED
tests/test_dockerfile.py::test_dockerfile_dev_installs_ta_lib PASSED
tests/test_dockerfile.py::test_dockerfile_prod_installs_ta_lib PASSED
tests/test_env_example.py::test_env_example_has_required_phase0_keys PASSED
tests/test_env_example.py::test_env_example_does_not_reference_openai PASSED
tests/test_gemini_client.py::test_get_chat_model_is_lazy_and_cached PASSED
tests/test_gemini_client.py::test_get_embedding_model_is_lazy_and_cached PASSED
tests/test_health.py::test_health_check_returns_ok PASSED
tests/test_health.py::test_root_returns_message PASSED
tests/test_migrations.py::test_migration_0001_workspaces_exists PASSED
tests/test_migrations.py::test_migration_0002_audit_log_exists PASSED
tests/test_migrations.py::test_migration_0003_allocation_plans_exists PASSED
tests/test_migrations.py::test_migration_0004_transactions_exists PASSED
tests/test_migrations.py::test_migration_0005_pin_codes_exists PASSED
tests/test_migrations.py::test_migration_0006_regulation_documents_exists PASSED
tests/test_migrations.py::test_migration_0007_rls_policies_exists PASSED
tests/test_pinecone_client.py::test_get_pinecone_client_is_lazy_and_cached PASSED
tests/test_pinecone_client.py::test_get_index_returns_handle_for_configured_index PASSED
tests/test_smoke.py::test_all_phase0_modules_import PASSED
tests/test_smoke.py::test_settings_loads_with_minimal_env PASSED
tests/test_smoke.py::test_clients_construct_without_error PASSED
tests/test_smoke.py::test_fastapi_app_constructs_and_health_works PASSED
tests/test_smoke.py::test_new_state_propagates_audit_id_through_messages PASSED
tests/test_state.py::test_agentstate_has_required_keys PASSED
tests/test_state.py::test_new_state_generates_audit_id_and_zero_revisions PASSED
tests/test_state.py::test_legal_status_enum_values PASSED
tests/test_supabase_admin.py::test_get_admin_client_uses_service_role_key PASSED
```

If any test fails, fix the corresponding code before proceeding.

### Task H2: Manual Docker boot check

- [ ] **Step 1: Configure your local .env**

Copy `.env.example` to `.env` and fill in real values for SUPABASE_*, GOOGLE_API_KEY, PINECONE_API_KEY, SUPABASE_SERVICE_ROLE_KEY. Use placeholder values for any keys you don't have yet — the backend boots even with placeholders thanks to the lazy clients.

- [ ] **Step 2: Boot the dev stack**

Run: `make dev`
Expected: All three services (frontend, backend, prometheus) come up. Backend logs show `Application startup complete`.

- [ ] **Step 3: Verify each endpoint**

Run in another terminal:

```bash
curl -s http://localhost:8000/api/v1/health
# Expected: {"status":"ok","version":"0.1.0"}

curl -s http://localhost:9090/-/ready
# Expected: "Prometheus Server is Ready."

curl -s http://localhost:3000 | head -c 200
# Expected: HTML response from Next.js
```

- [ ] **Step 4: Capture a screenshot or log snippet**

Save proof of the three endpoints responding (paste into the PR description or attach to the phase DoD ticket).

- [ ] **Step 5: Tear down**

Run: `make down`

### Task H3: Apply migrations to Supabase

- [ ] **Step 1: Apply each SQL file in order**

Open Supabase Studio → SQL Editor → run `0001` through `0007` in order, per `backend/migrations/README.md`.

- [ ] **Step 2: Verify in Table Editor**

Confirm each of `workspaces`, `audit_log`, `allocation_plans`, `transactions`, `pin_codes`, `regulation_documents` appears with the expected columns and the **RLS enabled** badge is green.

- [ ] **Step 3: RLS smoke test**

In SQL Editor, run as the `anon` role:

```sql
set role anon;
select * from public.workspaces;
-- Expected: empty result (anon has no auth.uid() so no rows match)
reset role;
```

This proves deny-by-default works.

### Task H4: Phase 0 sign-off commit

- [ ] **Step 1: Tag the foundation as complete**

Confirm `git status` is clean and create a tag/marker:

```bash
git tag -a phase-0-complete -m "AstaLink Phase 0 — foundation (deps, clients, state, schema, observability stub)"
```

(Tag is local-only unless you `git push --tags`; that's optional and up to the team.)

---

## Phase 0 Definition of Done

All of the following must be true before Phase 1 starts:

- [ ] All 37 tests in `backend/tests/` pass on a clean `uv sync --extra dev` (2 health + 2 chat + 1 deps + 2 dockerfile + 2 env_example + 3 compose + 5 config + 2 gemini + 2 pinecone + 1 supabase_admin + 3 state + 7 migrations + 5 smoke).
- [ ] `make dev` boots frontend + backend + prometheus without errors.
- [ ] `GET /api/v1/health` returns 200; `prometheus:9090/-/ready` returns ready.
- [ ] All 7 SQL migrations are applied to the project's Supabase instance; the 6 tables exist with RLS enabled.
- [ ] RLS smoke test passes (anon role gets empty result on workspace queries).
- [ ] No `OPENAI_API_KEY` references remain in the codebase: `grep -ri OPENAI_API_KEY .` returns no application-code matches.
- [ ] `AgentState` is importable from `app.agents.state` and has all 11 contracted fields.
- [ ] `.env.example` is complete and documented.
- [ ] Phase 0 sub-plan checkboxes are all checked.

When all items are checked, write a brief Phase 0 retro (1 paragraph: what worked, what surprised us, anything Phase 1 should know) and proceed to writing the Phase 1 sub-plan.
