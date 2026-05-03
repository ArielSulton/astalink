# Astalink Template

A production-ready monorepo template for building AI-powered web applications.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16+ (App Router) + Shadcn UI + Tailwind CSS |
| Backend | FastAPI + LangGraph |
| Database & Auth | Supabase |
| Infrastructure | Docker Compose (dev + prod) + Nginx |

## Prerequisites

- Node.js 20+
- Python 3.12+
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker & Docker Compose v2

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env with your Supabase project values
```

Get your values from your [Supabase Dashboard](https://supabase.com/dashboard):
- `SUPABASE_URL` → Project Settings → API → Project URL
- `SUPABASE_ANON_KEY` → Project Settings → API → anon public key
- `SUPABASE_JWT_SECRET` → Project Settings → API → JWT Secret

### 2. Development

```bash
make dev
# or
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs (dev only)

### 3. Production

```bash
make prod
# or
docker compose -f docker-compose.prod.yml up --build -d
```

App served at http://localhost via Nginx.

## Project Structure

```
astalink/
├── frontend/    # Next.js App Router + Shadcn UI
├── backend/     # FastAPI + LangGraph
├── nginx/       # Production reverse proxy config
├── docker-compose.yml       # Dev environment
└── docker-compose.prod.yml  # Production environment
```

## Auth Flow

1. User signs up/logs in via Supabase Auth (frontend)
2. Supabase issues a JWT stored in cookies
3. Next.js middleware refreshes the session on every request
4. Protected routes redirect unauthenticated users to `/login`
5. Backend verifies Supabase JWT on protected API endpoints

## Adding a New LangGraph Agent

1. Create `backend/app/agents/your_agent.py` with a `StateGraph`
2. Add a new router in `backend/app/api/v1/your_endpoint.py`
3. Register in `backend/app/api/v1/router.py`
4. Write tests in `backend/tests/test_your_endpoint.py`

## Running Tests

```bash
# Backend
make test-backend

# Frontend type check
cd frontend && npx tsc --noEmit
```
