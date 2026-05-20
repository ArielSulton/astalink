# Deploying AstaLink on Dokploy

## Prerequisites
- A Dokploy host with Traefik enabled and a domain pointing at it.
- Cloudflare/registrar A record `astalink.<your-domain>` → Dokploy host IP.
- Supabase project with all migrations (0001–0009) applied.
- Pinecone index named `astalink-regulations` provisioned (or matching `PINECONE_INDEX_NAME`).
- Google Gemini API key with chat + embedding access.
- Meta WhatsApp Business API verified phone number + tokens (optional — defer if not ready).

## Steps

1. **Dokploy → New Project → Compose.**
2. Repository: this repo. Compose file: `docker-compose.prod.yml`. Branch: `main` (or your release branch).
3. **Environment Variables** — paste the contents of `.env.example` and fill in real values. Critical keys:
   - `PROD_DOMAIN=https://astalink.<your-domain>`
   - `PROD_DOMAIN_HOST=astalink.<your-domain>` (bare hostname for Traefik label rules)
   - `GRAFANA_ADMIN_PASSWORD=<strong-password>` (NOT the default `change-me`)
   - All Supabase keys (anon, JWT secret, service-role, DB URL — use the production project, not the eval/staging one)
   - `GOOGLE_API_KEY`, `PINECONE_API_KEY` (production-tier accounts)
   - `WHATSAPP_*` (only if Meta verification is complete; otherwise leave blank — webhook returns 403 until set)
   - `APP_BASE_URL=${PROD_DOMAIN}`
4. **Deploy.** Watch logs for:
   - `frontend`: Next.js readiness (`Ready in N ms`)
   - `backend`: `Application startup complete`
   - `prometheus`: `Server is ready to receive web requests`
   - `grafana`: `HTTP Server Listen ... addr=:3000`
5. **Verify endpoints:**
   ```bash
   curl -fsSL https://astalink.<your-domain>/api/v1/health
   # → {"status":"ok","version":"0.1.0"}
   curl -fsSL -I https://astalink.<your-domain>/grafana/login
   # → HTTP 200 (Grafana login page)
   ```
6. **Apply migrations:** in Supabase Studio SQL Editor, run `0001` through `0009` in order. (If a staging Supabase project already has earlier migrations, only run the new ones.)
7. **Configure Meta WhatsApp webhook** to `https://astalink.<your-domain>/api/v1/whatsapp/webhook` (only after `WHATSAPP_VERIFY_TOKEN` is set in Dokploy env). Verify Meta returns the challenge.

## Smoke-test runbook

1. Sign up via web (`/signup`) → confirm Supabase auth works in prod.
2. Create a workspace via Supabase Studio (or via UI when the workspace creation form ships).
3. Set a PIN at `/settings/pin`.
4. Run `POST /api/v1/agent/run` with a test allocation:
   ```bash
   curl -X POST https://astalink.<your-domain>/api/v1/agent/run \
     -H "Authorization: Bearer <user-JWT>" \
     -H "Content-Type: application/json" \
     -d '{"message":"alokasikan 10jt ke BBCA dan BMRI","workspace_id":"<id>"}'
   ```
   Expect a response with `legal_status`, `allocation_plan`, and either `transactions` (auto-mode happy path) or a HITL pause.
5. Approve via `/approvals/<audit_id>` — enter PIN, watch graph resume.
6. Verify `/transactions` shows the (sandbox) fill.
7. Open Grafana → AstaLink folder → see live data on all three dashboards within 1 minute of the run.

## Rollback

Dokploy preserves the last successful image; revert via the deployment history.

Postgres data is in Supabase (separately managed) so app rollback is decoupled from data state. If a migration was applied that needs reverting, write a `down` SQL file manually and apply via Supabase Studio.

## Limitations / future work

- **No Loki/ELK** — `docker logs` via Dokploy is the log source. Add log aggregation post-hackathon.
- **No alerting** — set up Grafana → Alerting after the first prod week. Suggested first rule: `rate(astalink_node_errors_total[5m]) > 0.1`.
- **No autoscaling** — single replica per service.
- **`RealBroker` is a stub** — placing real orders requires wiring an Indonesian retail broker's HTTP API; `SandboxBroker` is what runs in prod today.
