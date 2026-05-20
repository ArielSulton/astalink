# AstaLink Phase 8 — Monitoring, Quality Gates, Production Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. **Phases 0–7 must be complete (or at minimum Phases 0–5 — Phase 8's observability work is useful even without WhatsApp/execution).**

**Goal:** Make AstaLink operationally legible: HTTP + per-LangGraph-node Prometheus metrics, Grafana dashboards, a DeepEval-driven CI quality gate, and a production deploy on Dokploy with Traefik routing + HTTPS. After this phase, every demo and every prod incident has data to back it up.

**Architecture:**
- **Metrics:** `prometheus-fastapi-instrumentator` for HTTP latency/throughput; custom Prometheus collectors for per-node duration, error rate, revision-count histogram, and legal-status counters. `/metrics` endpoint exposed (already scraped by the Phase 0 Prometheus container).
- **Grafana:** Auto-provisioned dashboards via `grafana/provisioning/dashboards/`. Three boards: pipeline health, AI quality (DeepEval scores ingested as gauges), business funnel (approvals/rejections/executions per day).
- **CI quality gate:** `.github/workflows/quality-gate.yml` runs the DeepEval slow suite on PRs touching `app/agents/legal/` or `app/agents/{market,business,risk}/`; fails if hallucination drops below 0.95 or factuality below 0.9.
- **Prod deploy:** rewrite `docker-compose.prod.yml` to drop nginx and add Traefik labels for Dokploy. Secrets come from Dokploy env vars. Traefik handles HTTPS via Let's Encrypt against `PROD_DOMAIN`.

**Tech Stack:** prometheus-fastapi-instrumentator, prometheus_client, Grafana provisioning files, GitHub Actions, Traefik 3.x labels, Dokploy hosted runtime.

**Scope cuts:** No log aggregation in this phase (Loki/ELK is post-hackathon; stdout + Dokploy log viewer is enough). No alerting rules (set them up after first prod week). No multi-region. No autoscaling.

---

## File Structure

```
backend/
├── app/
│   ├── core/
│   │   └── metrics.py              # CREATE: registry + helper decorators
│   └── main.py                     # MODIFY: register instrumentator
├── tests/
│   └── test_metrics.py             # CREATE

grafana/
├── provisioning/
│   ├── dashboards/
│   │   └── astalink.yml            # CREATE: auto-load dashboards
│   └── datasources/
│       └── prometheus.yml          # CREATE: point at the prometheus container
└── dashboards/
    ├── pipeline-health.json        # CREATE
    ├── ai-quality.json             # CREATE
    └── business-funnel.json        # CREATE

.github/
└── workflows/
    └── quality-gate.yml            # CREATE

docker-compose.prod.yml             # REWRITE: Traefik labels, drop nginx
docker-compose.yml                  # MODIFY: add grafana service alongside prometheus
nginx/                              # DELETE (replaced by Traefik)
```

---

## Task Group A — Metrics Instrumentation

### Task A1: Custom metrics registry

**Files:**
- Create: `backend/app/core/metrics.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_metrics.py`

- [ ] **Step 1: Write failing test**

`backend/tests/test_metrics.py`:

```python
import time
from fastapi.testclient import TestClient


def test_metrics_endpoint_exposes_prometheus_format(client: TestClient) -> None:
    # Trigger at least one request so HTTP histograms have data
    client.get("/api/v1/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    # Default instrumentator metrics
    assert "http_request_duration_seconds" in text
    # AstaLink custom metrics
    assert "astalink_node_duration_seconds" in text
    assert "astalink_legal_status_total" in text
    assert "astalink_revision_count" in text


def test_track_node_duration_decorator_records_histogram() -> None:
    from app.core.metrics import track_node_duration
    from prometheus_client import REGISTRY

    @track_node_duration("test_node")
    def some_node(state):
        time.sleep(0.01)
        return state

    some_node({})
    samples = [s for m in REGISTRY.collect() for s in m.samples
               if s.name.startswith("astalink_node_duration_seconds")
               and s.labels.get("node") == "test_node"]
    # Histogram emits _count, _sum, _bucket
    assert any(s.name == "astalink_node_duration_seconds_count" for s in samples)


def test_record_legal_status_increments_counter() -> None:
    from app.core.metrics import record_legal_status
    from prometheus_client import REGISTRY

    record_legal_status("approved")
    record_legal_status("approved")
    record_legal_status("rejected")

    samples = {(s.labels.get("status"),): s.value for m in REGISTRY.collect()
               for s in m.samples if s.name == "astalink_legal_status_total"}
    assert samples.get(("approved",), 0) >= 2
    assert samples.get(("rejected",), 0) >= 1
```

- [ ] **Step 2: Implement**

`backend/app/core/metrics.py`:

```python
"""Prometheus metrics: registry + helpers + decorators.

Usage in nodes:
    @track_node_duration("n3_legal")
    def legal_node(state): ...

Or for ad-hoc events:
    record_legal_status("approved")
    record_revision_count(state["revision_count"])
"""
from __future__ import annotations

import time
from functools import wraps

from prometheus_client import Counter, Histogram

NODE_DURATION = Histogram(
    "astalink_node_duration_seconds",
    "Wall-clock duration of a LangGraph node invocation",
    labelnames=["node"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)

NODE_ERRORS = Counter(
    "astalink_node_errors_total",
    "Number of node invocations that returned an error in state.errors",
    labelnames=["node"],
)

LEGAL_STATUS = Counter(
    "astalink_legal_status_total",
    "Distribution of Legal Agent decisions",
    labelnames=["status"],
)

REVISION_COUNT = Histogram(
    "astalink_revision_count",
    "Final revision_count per pipeline run",
    buckets=(0, 1, 2, 3, 4, 5),
)

EXECUTIONS = Counter(
    "astalink_executions_total",
    "Number of orders placed by N7",
    labelnames=["status"],
)


def track_node_duration(node_name: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                NODE_DURATION.labels(node=node_name).observe(time.perf_counter() - t0)
        return wrapper
    return decorator


def record_legal_status(status: str) -> None:
    LEGAL_STATUS.labels(status=status).inc()


def record_revision_count(n: int) -> None:
    REVISION_COUNT.observe(n)


def record_execution(status: str) -> None:
    EXECUTIONS.labels(status=status).inc()


def record_node_error(node_name: str) -> None:
    NODE_ERRORS.labels(node=node_name).inc()
```

- [ ] **Step 3: Wire into main.py**

`backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.core.config import settings
import app.core.metrics  # noqa: F401  — registers collectors

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# Mount /metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/")
async def root():
    return {"message": "Astalink Backend", "version": settings.APP_VERSION}
```

- [ ] **Step 4: Decorate the real nodes**

Add `@track_node_duration("n1_intent")` on `intent_node`, `@track_node_duration("n3_legal")` on `legal_node`, etc. In the legal node, after the decision is made, also call `record_legal_status(decision.status.value)`. In the optimizer node, call `record_revision_count(state.get("revision_count", 0) + 1)` at the end. In the execution node, call `record_execution(order.status)` per fill.

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run python -m pytest tests/test_metrics.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/metrics.py backend/app/main.py backend/app/agents backend/tests/test_metrics.py
git commit -m "feat(metrics): Prometheus instrumentation for HTTP + per-node duration + legal status"
```

---

## Task Group B — Grafana Provisioning

### Task B1: Datasource + dashboard provisioning files

**Files:**
- Create: `grafana/provisioning/datasources/prometheus.yml`
- Create: `grafana/provisioning/dashboards/astalink.yml`
- Create: `grafana/dashboards/pipeline-health.json` (and ai-quality, business-funnel)
- Modify: `docker-compose.yml` to add Grafana service

- [ ] **Step 1: Create datasource provisioning**

`grafana/provisioning/datasources/prometheus.yml`:

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

- [ ] **Step 2: Create dashboard provisioner**

`grafana/provisioning/dashboards/astalink.yml`:

```yaml
apiVersion: 1
providers:
  - name: AstaLink
    folder: AstaLink
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

- [ ] **Step 3: Pipeline-health dashboard**

`grafana/dashboards/pipeline-health.json` — minimum panels: per-node p95 latency (heatmap from `astalink_node_duration_seconds_bucket`), per-node error rate (`rate(astalink_node_errors_total[5m])`), HTTP request rate (`rate(http_request_duration_seconds_count[5m])`).

The exact JSON is large; build it interactively in Grafana UI then export with **"Share → Export → Save to file"** and commit. Skeleton:

```json
{
  "title": "AstaLink Pipeline Health",
  "uid": "astalink-pipeline",
  "panels": [
    {
      "title": "Node duration p95 by node",
      "type": "timeseries",
      "targets": [{
        "expr": "histogram_quantile(0.95, sum by (node, le) (rate(astalink_node_duration_seconds_bucket[5m])))",
        "legendFormat": "{{node}}"
      }]
    }
  ],
  "schemaVersion": 39
}
```

- [ ] **Step 4: AI quality dashboard**

`grafana/dashboards/ai-quality.json` — panels for `astalink_legal_status_total` rate by status (stacked area), `astalink_revision_count` histogram, DeepEval gauge (push from CI as `astalink_deepeval_hallucination`).

- [ ] **Step 5: Business funnel dashboard**

`grafana/dashboards/business-funnel.json` — counter increments over time: `astalink_legal_status_total{status="approved"}`, `astalink_executions_total{status="filled"}`. A simple funnel: requests → approved → executed.

- [ ] **Step 6: Add Grafana to docker-compose.yml**

```yaml
  grafana:
    image: grafana/grafana:11.1.0
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:
```

- [ ] **Step 7: Smoke-test**

Run `make dev`. Visit `http://localhost:3001`. Log in as admin/admin. Confirm "AstaLink" folder exists with the three dashboards. Verify each dashboard shows live data after running an `agent/run` end-to-end.

- [ ] **Step 8: Commit**

```bash
git add grafana docker-compose.yml
git commit -m "feat(grafana): provisioning for pipeline-health + ai-quality + business-funnel dashboards"
```

---

## Task Group C — DeepEval CI Quality Gate

### Task C1: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/quality-gate.yml`

- [ ] **Step 1: Write the workflow**

`.github/workflows/quality-gate.yml`:

```yaml
name: AI Quality Gate

on:
  pull_request:
    paths:
      - "backend/app/agents/legal/**"
      - "backend/app/agents/market/**"
      - "backend/app/agents/business/**"
      - "backend/app/agents/risk/**"
      - "backend/tests/test_legal_hallucination.py"
      - "backend/tests/data/eval_prompts.json"

jobs:
  deepeval:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Install system deps (TA-Lib)
        run: |
          sudo apt-get update
          sudo apt-get install -y build-essential wget
          wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
          tar -xzf ta-lib-0.4.0-src.tar.gz
          cd ta-lib && ./configure --prefix=/usr && sudo make && sudo make install
      - name: Install backend deps
        working-directory: backend
        run: |
          uv sync --extra dev
          uv pip install ta-lib
      - name: Run DeepEval slow suite
        working-directory: backend
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          PINECONE_API_KEY: ${{ secrets.PINECONE_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
          SUPABASE_JWT_SECRET: ${{ secrets.SUPABASE_JWT_SECRET }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
        run: |
          uv run python -m pytest tests/test_legal_hallucination.py -v -m slow
```

Configure GitHub repo secrets: `GOOGLE_API_KEY`, `PINECONE_API_KEY`, the Supabase keys (use a dedicated **eval-only** Supabase project to avoid touching prod data).

- [ ] **Step 2: Commit and verify on a PR**

```bash
git add .github/workflows/quality-gate.yml
git commit -m "ci(quality-gate): run DeepEval slow suite on legal/analyzer changes"
```

Open a small PR touching `app/agents/legal/` to verify the gate runs and passes.

---

## Task Group D — Production Deploy (Dokploy + Traefik)

### Task D1: Rewrite docker-compose.prod.yml with Traefik labels

**Files:**
- Rewrite: `docker-compose.prod.yml`
- Delete: `nginx/` directory (no longer needed)

- [ ] **Step 1: Implement**

`docker-compose.prod.yml`:

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    environment:
      - NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}
      - NEXT_PUBLIC_BACKEND_URL=${PROD_DOMAIN}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.astalink-fe.rule=Host(`${PROD_DOMAIN_HOST}`)"
      - "traefik.http.routers.astalink-fe.entrypoints=websecure"
      - "traefik.http.routers.astalink-fe.tls.certresolver=letsencrypt"
      - "traefik.http.services.astalink-fe.loadbalancer.server.port=3000"
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    environment:
      # Supabase
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - SUPABASE_DB_URL=${SUPABASE_DB_URL}
      # Gemini
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - GEMINI_CHAT_MODEL=${GEMINI_CHAT_MODEL:-gemini-1.5-flash}
      - GEMINI_EMBEDDING_MODEL=${GEMINI_EMBEDDING_MODEL:-text-embedding-004}
      # Pinecone
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_INDEX_NAME=${PINECONE_INDEX_NAME:-astalink-regulations}
      # WhatsApp
      - WHATSAPP_VERIFY_TOKEN=${WHATSAPP_VERIFY_TOKEN}
      - WHATSAPP_APP_SECRET=${WHATSAPP_APP_SECRET}
      - WHATSAPP_ACCESS_TOKEN=${WHATSAPP_ACCESS_TOKEN}
      - WHATSAPP_PHONE_NUMBER_ID=${WHATSAPP_PHONE_NUMBER_ID}
      # News
      - NEWS_API_KEY=${NEWS_API_KEY}
      # App
      - APP_BASE_URL=${PROD_DOMAIN}
      - DEBUG=false
      - BACKEND_CORS_ORIGINS=["${PROD_DOMAIN}"]
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.astalink-be.rule=Host(`${PROD_DOMAIN_HOST}`) && PathPrefix(`/api`)"
      - "traefik.http.routers.astalink-be.entrypoints=websecure"
      - "traefik.http.routers.astalink-be.tls.certresolver=letsencrypt"
      - "traefik.http.services.astalink-be.loadbalancer.server.port=8000"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:v2.55.0
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:11.1.0
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_SERVER_ROOT_URL=${PROD_DOMAIN}/grafana/
      - GF_SERVER_SERVE_FROM_SUB_PATH=true
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana_data:/var/lib/grafana
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.astalink-grafana.rule=Host(`${PROD_DOMAIN_HOST}`) && PathPrefix(`/grafana`)"
      - "traefik.http.routers.astalink-grafana.entrypoints=websecure"
      - "traefik.http.routers.astalink-grafana.tls.certresolver=letsencrypt"
      - "traefik.http.services.astalink-grafana.loadbalancer.server.port=3000"
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:
```

Add `PROD_DOMAIN_HOST` (the bare hostname, e.g. `astalink.your-domain.com`) and `GRAFANA_ADMIN_PASSWORD` to `.env.example`. Note: Dokploy's bundled Traefik already runs as the network ingress — this compose file only declares labels; no Traefik service is included here.

- [ ] **Step 2: Delete nginx**

```bash
rm -r nginx
```

- [ ] **Step 3: Update Makefile**

In `Makefile`, the `prod` target stays the same (`docker compose -f docker-compose.prod.yml up --build -d`) but document that production should be deployed via Dokploy, not run locally.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.prod.yml .env.example Makefile
git rm -r nginx
git commit -m "feat(deploy): switch prod from nginx to Traefik labels for Dokploy"
```

---

### Task D2: Dokploy deploy steps (manual runbook)

**Files:**
- Create: `docs/deploy/dokploy.md`

This is a documentation-only task; Dokploy is configured via UI.

- [ ] Create `docs/deploy/dokploy.md` with:

```markdown
# Deploying AstaLink on Dokploy

## Prerequisites
- A Dokploy host with Traefik enabled and a domain pointing at it.
- Cloudflare/registrar A record `astalink.<your-domain>` → Dokploy host IP.

## Steps
1. Dokploy → New Project → Compose.
2. Repository: this repo. Compose file: `docker-compose.prod.yml`. Branch: `main`.
3. **Environment Variables** — paste the contents of `.env.example` and fill in real values. CRITICAL keys:
   - `PROD_DOMAIN=https://astalink.<your-domain>`
   - `PROD_DOMAIN_HOST=astalink.<your-domain>`
   - All Supabase keys (use the production project, not eval)
   - `GOOGLE_API_KEY`, `PINECONE_API_KEY` (production-tier)
   - `WHATSAPP_*` (only if Meta verification is complete)
4. Hit Deploy. Watch logs for `Application startup complete` from backend, frontend Next.js readiness, Prometheus + Grafana boots.
5. Verify:
   - `https://astalink.<your-domain>/api/v1/health` returns `{"status":"ok"}`
   - `https://astalink.<your-domain>` shows the Next.js login page
   - `https://astalink.<your-domain>/grafana` shows Grafana login (admin / GRAFANA_ADMIN_PASSWORD)
6. Apply migrations: in Supabase Studio, run `0001`–`0009` in order. Re-run from where you left off if some were already applied to a staging project.
7. Configure Meta WhatsApp webhook to `https://astalink.<your-domain>/api/v1/whatsapp/webhook` (only after WHATSAPP_VERIFY_TOKEN is set in Dokploy env).

## Smoke-test runbook
1. Sign up via web (`/signup`) → confirm Supabase auth works in prod.
2. Create a workspace.
3. Set a PIN at `/settings/pin`.
4. Run `POST /api/v1/agent/run` with a test allocation.
5. Approve via `/approvals`.
6. Verify `/transactions` shows the (sandbox) fill.
7. Open Grafana → AstaLink folder → see live data on all three dashboards.

## Rollback
Dokploy preserves the last successful image; revert via the deployment history. Postgres data is in Supabase (separately managed) so app rollback is decoupled from data state.
```

- [ ] **Step 1: Commit**

```bash
git add docs/deploy/dokploy.md
git commit -m "docs(deploy): Dokploy deployment runbook"
```

---

## Phase 8 Definition of Done

- [ ] All Phase 0–7 tests still pass; metrics tests pass.
- [ ] `/metrics` endpoint exposes both default HTTP metrics and AstaLink custom metrics.
- [ ] Grafana dashboards load with live data after running an end-to-end agent flow.
- [ ] CI quality gate is green on a PR touching `app/agents/legal/`.
- [ ] Production deployment on Dokploy is reachable at `https://astalink.<your-domain>` with HTTPS via Let's Encrypt.
- [ ] All Phase 0–7 demo paths reproducible in prod (sign up, set PIN, agent run, approve, execute, see transactions, Grafana dashboards).
- [ ] Dokploy deploy runbook is checked in.
- [ ] First-week alerting: at minimum, set up an email/Slack alert from Grafana when `rate(astalink_node_errors_total[5m]) > 0.1` — this can be a follow-up but should be on the team's mind.
