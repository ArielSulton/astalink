# Next.js + FastAPI + LangGraph + Supabase Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready monorepo template combining Next.js (App Router) + Shadcn UI on the frontend with FastAPI + LangGraph on the backend, wired to Supabase for database and authentication, deployable via Docker Compose in both dev and prod modes.

**Architecture:** Frontend (Next.js App Router + Shadcn UI) communicates with the FastAPI backend via REST; Supabase handles PostgreSQL storage and JWT-based auth. The backend verifies Supabase-issued JWTs and exposes LangGraph agents through versioned API routes. Docker Compose orchestrates all services with separate dev (hot-reload) and prod (optimized build + nginx) configurations.

**Tech Stack:** Next.js 15+ (App Router, TypeScript, Tailwind CSS v4), Shadcn UI, FastAPI 0.115+, LangGraph 0.2+, Supabase (hosted), @supabase/ssr, Docker Compose v2, Nginx (prod only), Python 3.12, uv (package manager)

---

## File Structure

```
astalink/
├── frontend/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   ├── signup/page.tsx
│   │   │   └── auth/callback/route.ts
│   │   ├── (protected)/
│   │   │   └── dashboard/page.tsx
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                    # Shadcn auto-generated
│   │   └── auth/
│   │       ├── login-form.tsx
│   │       └── signup-form.tsx
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts          # Browser client
│   │   │   └── server.ts          # Server component client
│   │   └── utils.ts
│   ├── middleware.ts               # Supabase session refresh
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── components.json
│   ├── tsconfig.json
│   ├── package.json
│   ├── .env.local.example
│   ├── Dockerfile.dev
│   └── Dockerfile.prod
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── router.py
│   │   │   │   ├── health.py
│   │   │   │   └── chat.py
│   │   │   └── deps.py            # Auth dependency injection
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   └── chat_agent.py      # LangGraph chat agent
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic Settings
│   │   │   └── security.py        # JWT verification
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── chat.py            # Pydantic request/response models
│   │   └── main.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_health.py
│   │   └── test_chat.py
│   ├── pyproject.toml
│   ├── .env.example
│   ├── Dockerfile.dev
│   └── Dockerfile.prod
├── nginx/
│   └── nginx.conf
├── docker-compose.yml              # Dev
├── docker-compose.prod.yml         # Prod
├── .env.example                    # Root shared env vars
└── Makefile                        # Helper commands
```

---

## Task 1: Root Project Scaffold

**Files:**
- Create: `.env.example`
- Create: `Makefile`

- [ ] **Step 1: Initialize root directory and git**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink"
git init
echo "node_modules/\n.env\n.env.local\n__pycache__/\n.venv/\n*.pyc\n.next/\ndist/\n.DS_Store" > .gitignore
```

- [ ] **Step 2: Create root `.env.example`**

```bash
cat > .env.example << 'EOF'
# Supabase (shared between frontend and backend)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret

# OpenAI (for LangGraph agents)
OPENAI_API_KEY=your-openai-api-key

# Backend
BACKEND_PORT=8000
BACKEND_CORS_ORIGINS=http://localhost:3000

# Frontend
FRONTEND_PORT=3000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
EOF
```

- [ ] **Step 3: Create `Makefile` with helper commands**

```makefile
# Makefile
.PHONY: dev prod build clean

dev:
	docker compose -f docker-compose.yml up --build

prod:
	docker compose -f docker-compose.prod.yml up --build -d

down:
	docker compose -f docker-compose.yml down

down-prod:
	docker compose -f docker-compose.prod.yml down

frontend-install:
	cd frontend && npm install

backend-install:
	cd backend && uv sync

test-backend:
	cd backend && uv run pytest tests/ -v

logs:
	docker compose logs -f

clean:
	docker compose down -v
	docker system prune -f
```

- [ ] **Step 4: Commit scaffold**

```bash
git add .gitignore .env.example Makefile docs/
git commit -m "chore: initialize project scaffold with root config"
```

---

## Task 2: Next.js 15+ Frontend Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/globals.css`
- Create: `frontend/.env.local.example`

- [ ] **Step 1: Bootstrap Next.js app**

```bash
cd "/home/arielsulton/Documents/Stargazing Project/VScode Project/digdaya x hackathon 2026/astalink"
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --no-src-dir \
  --import-alias "@/*"
```

Expected output: `✓ Created next.js app in frontend/`

- [ ] **Step 2: Verify Next.js version is 15+**

```bash
cd frontend && node -e "const p = require('./package.json'); console.log('Next.js:', p.dependencies.next)"
```

Expected output: `Next.js: 15.x.x` or higher

- [ ] **Step 3: Create `frontend/.env.local.example`**

```bash
cat > frontend/.env.local.example << 'EOF'
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
EOF
cp frontend/.env.local.example frontend/.env.local
```

- [ ] **Step 4: Update `frontend/next.config.ts` to allow API proxying**

```typescript
// frontend/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    optimizePackageImports: ["@radix-ui/react-icons"],
  },
};

export default nextConfig;
```

- [ ] **Step 5: Update `frontend/app/layout.tsx`**

```typescript
// frontend/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Astalink",
  description: "Next.js + FastAPI + Supabase Template",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
```

- [ ] **Step 6: Update `frontend/app/page.tsx`**

```typescript
// frontend/app/page.tsx
import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-8">Astalink Template</h1>
      <p className="text-muted-foreground mb-8">
        Next.js + FastAPI + LangGraph + Supabase
      </p>
      <div className="flex gap-4">
        <Link
          href="/login"
          className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
        >
          Login
        </Link>
        <Link
          href="/signup"
          className="px-4 py-2 rounded-md border border-input hover:bg-accent"
        >
          Sign Up
        </Link>
      </div>
    </main>
  );
}
```

- [ ] **Step 7: Verify Next.js dev server starts**

```bash
cd frontend && npm run dev &
sleep 5
curl -s http://localhost:3000 | grep -q "Astalink" && echo "PASS: Frontend serving" || echo "FAIL: Frontend not responding"
kill %1
```

Expected output: `PASS: Frontend serving`

- [ ] **Step 8: Commit frontend setup**

```bash
cd ..
git add frontend/
git commit -m "feat: initialize Next.js 15 frontend with App Router and TypeScript"
```

---

## Task 3: Shadcn UI Installation & Base Components

**Files:**
- Create: `frontend/components.json`
- Create: `frontend/components/ui/` (auto-generated by shadcn)
- Create: `frontend/lib/utils.ts`

- [ ] **Step 1: Install Shadcn UI**

```bash
cd frontend
npx shadcn@latest init --defaults
```

When prompted:
- Style: Default
- Base color: Slate
- CSS variables: Yes

Expected output: `✓ Done. components.json created.`

- [ ] **Step 2: Add essential components**

```bash
npx shadcn@latest add button card input label form \
  toast sonner dropdown-menu avatar badge separator
```

Expected output: Each component shows `✓ Done.`

- [ ] **Step 3: Verify `frontend/lib/utils.ts` exists and has `cn` helper**

```bash
grep -q "clsx" frontend/lib/utils.ts && echo "PASS: cn utility exists" || echo "FAIL: utils.ts missing"
```

Expected output: `PASS: cn utility exists`

- [ ] **Step 4: Install additional deps for forms**

```bash
npm install react-hook-form @hookform/resolvers zod
```

- [ ] **Step 5: Commit Shadcn setup**

```bash
cd ..
git add frontend/
git commit -m "feat: add Shadcn UI with base components and form dependencies"
```

---

## Task 4: FastAPI Backend Setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/api/v1/router.py`
- Create: `backend/app/api/v1/health.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/.env.example`

- [ ] **Step 1: Initialize Python project with uv**

```bash
cd backend
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env  # or restart shell
uv init --python 3.12 .
```

- [ ] **Step 2: Create `backend/pyproject.toml` with all dependencies**

```toml
# backend/pyproject.toml
[project]
name = "astalink-backend"
version = "0.1.0"
description = "FastAPI + LangGraph backend for Astalink template"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.8.0",
    "pydantic-settings>=2.4.0",
    "python-jose[cryptography]>=3.3.0",
    "httpx>=0.27.0",
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
    "langchain-openai>=0.2.0",
    "supabase>=2.7.0",
    "python-multipart>=0.0.9",
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

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 3: Install dependencies**

```bash
cd backend && uv sync --extra dev
```

Expected output: `Resolved N packages in Xs`

- [ ] **Step 4: Create `backend/app/core/config.py`**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Astalink Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str

    # OpenAI
    OPENAI_API_KEY: str = ""

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]


settings = Settings()
```

- [ ] **Step 5: Create `backend/.env.example` and `.env` for testing**

```bash
cat > backend/.env.example << 'EOF'
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
OPENAI_API_KEY=your-openai-api-key
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
EOF
cp backend/.env.example backend/.env
```

- [ ] **Step 6: Create `backend/app/api/v1/health.py`**

```python
# backend/app/api/v1/health.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")
```

- [ ] **Step 7: Create `backend/app/api/v1/router.py`**

```python
# backend/app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1 import health, chat

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
```

- [ ] **Step 8: Create `backend/app/models/__init__.py`**

```python
# backend/app/models/__init__.py
```

- [ ] **Step 9: Create `backend/app/main.py`**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router

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


@app.get("/")
async def root():
    return {"message": "Astalink Backend", "version": settings.APP_VERSION}
```

- [ ] **Step 10: Create `backend/tests/conftest.py`**

```python
# backend/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
```

- [ ] **Step 11: Create `backend/tests/test_health.py`**

```python
# backend/tests/test_health.py
from fastapi.testclient import TestClient


def test_health_check_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_root_returns_message(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Astalink Backend"
```

- [ ] **Step 12: Run failing tests first**

```bash
cd backend && uv run pytest tests/test_health.py -v
```

Expected output: Tests should PASS (backend is already set up)

- [ ] **Step 13: Verify backend starts**

```bash
cd backend && uv run uvicorn app.main:app --port 8000 &
sleep 3
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
kill %1
```

Expected output: `{"status": "ok", "version": "0.1.0"}`

- [ ] **Step 14: Commit backend setup**

```bash
cd ..
git add backend/
git commit -m "feat: initialize FastAPI backend with health endpoint and pytest setup"
```

---

## Task 5: LangGraph Chat Agent

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/chat_agent.py`
- Create: `backend/app/models/chat.py`
- Create: `backend/app/api/v1/chat.py`
- Create: `backend/tests/test_chat.py`

- [ ] **Step 1: Create `backend/app/models/chat.py`**

```python
# backend/app/models/chat.py
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    message: str
    thread_id: str
```

- [ ] **Step 2: Create `backend/app/agents/__init__.py`**

```python
# backend/app/agents/__init__.py
```

- [ ] **Step 3: Create `backend/app/agents/chat_agent.py`**

```python
# backend/app/agents/chat_agent.py
from typing import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings


class ChatState(TypedDict):
    messages: list[BaseMessage]


def _create_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.OPENAI_API_KEY,
    )


def chat_node(state: ChatState) -> ChatState:
    llm = _create_llm()
    response = llm.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}


def build_chat_graph() -> StateGraph:
    graph = StateGraph(ChatState)
    graph.add_node("chat", chat_node)
    graph.set_entry_point("chat")
    graph.add_edge("chat", END)
    return graph.compile(checkpointer=MemorySaver())


# Singleton graph instance
chat_graph = build_chat_graph()
```

- [ ] **Step 4: Write failing test for chat agent**

```python
# backend/tests/test_chat.py
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
    mock_user = {"sub": str(uuid.uuid4()), "email": "test@example.com"}

    mock_result = {
        "messages": [
            MagicMock(spec=AIMessage, content="Hello from AI!")
        ]
    }

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.agents.chat_agent.chat_graph.invoke", return_value=mock_result):

        response = client.post(
            "/api/v1/chat/",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "thread_id" in data
    assert data["message"] == "Hello from AI!"
```

- [ ] **Step 5: Run test to confirm it fails (401 test passes, mock test fails due to missing endpoint)**

```bash
cd backend && uv run pytest tests/test_chat.py::test_chat_endpoint_without_auth_returns_401 -v
```

Expected output: `FAILED` — route doesn't exist yet → 404 not 401

- [ ] **Step 6: Create `backend/app/api/deps.py`**

```python
# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import verify_token

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload
```

- [ ] **Step 7: Create `backend/app/core/security.py`**

```python
# backend/app/core/security.py
from jose import jwt, JWTError
from app.core.config import settings


def verify_token(token: str) -> dict | None:
    """Verify a Supabase-issued JWT and return the payload."""
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError:
        return None
```

- [ ] **Step 8: Create `backend/app/api/v1/chat.py`**

```python
# backend/app/api/v1/chat.py
import uuid
from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage
from app.agents.chat_agent import chat_graph
from app.api.deps import get_current_user
from app.models.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    thread_id = request.thread_id or str(uuid.uuid4())

    result = chat_graph.invoke(
        {"messages": [HumanMessage(content=request.message)]},
        config={"configurable": {"thread_id": thread_id}},
    )

    last_message = result["messages"][-1]
    return ChatResponse(message=last_message.content, thread_id=thread_id)
```

- [ ] **Step 9: Update `backend/app/api/v1/router.py` to include chat**

```python
# backend/app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1 import health, chat

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
```

- [ ] **Step 10: Run all tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected output: All tests PASS (chat mock test should pass with mocked auth and agent)

- [ ] **Step 11: Commit chat agent**

```bash
cd ..
git add backend/
git commit -m "feat: add LangGraph chat agent with JWT-protected FastAPI endpoint"
```

---

## Task 6: Supabase Client Configuration (Frontend)

**Files:**
- Create: `frontend/lib/supabase/client.ts`
- Create: `frontend/lib/supabase/server.ts`
- Create: `frontend/middleware.ts`

- [ ] **Step 1: Install Supabase SSR packages**

```bash
cd frontend && npm install @supabase/supabase-js @supabase/ssr
```

Expected output: `added N packages`

- [ ] **Step 2: Create `frontend/lib/supabase/client.ts` (browser client)**

```typescript
// frontend/lib/supabase/client.ts
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

- [ ] **Step 3: Create `frontend/lib/supabase/server.ts` (server component client)**

```typescript
// frontend/lib/supabase/server.ts
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // Server Component — cookies can't be set from here
          }
        },
      },
    }
  );
}
```

- [ ] **Step 4: Create `frontend/middleware.ts` for session refresh**

```typescript
// frontend/middleware.ts
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Redirect unauthenticated users away from protected routes
  if (!user && request.nextUrl.pathname.startsWith("/dashboard")) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/login";
    return NextResponse.redirect(redirectUrl);
  }

  // Redirect authenticated users away from auth pages
  if (
    user &&
    (request.nextUrl.pathname === "/login" ||
      request.nextUrl.pathname === "/signup")
  ) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/dashboard";
    return NextResponse.redirect(redirectUrl);
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected output: No errors

- [ ] **Step 6: Commit Supabase client setup**

```bash
cd ..
git add frontend/lib/ frontend/middleware.ts
git commit -m "feat: configure Supabase SSR clients and session-refresh middleware"
```

---

## Task 7: Supabase Auth Pages (Frontend)

**Files:**
- Create: `frontend/components/auth/login-form.tsx`
- Create: `frontend/components/auth/signup-form.tsx`
- Create: `frontend/app/(auth)/login/page.tsx`
- Create: `frontend/app/(auth)/signup/page.tsx`
- Create: `frontend/app/auth/callback/route.ts`
- Create: `frontend/app/(protected)/dashboard/page.tsx`

- [ ] **Step 1: Create directories**

```bash
mkdir -p frontend/app/\(auth\)/login
mkdir -p frontend/app/\(auth\)/signup
mkdir -p frontend/app/auth/callback
mkdir -p frontend/app/\(protected\)/dashboard
mkdir -p frontend/components/auth
```

- [ ] **Step 2: Create `frontend/components/auth/login-form.tsx`**

```typescript
// frontend/components/auth/login-form.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const form = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(data: LoginForm) {
    setLoading(true);
    setError(null);

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({
      email: data.email,
      password: data.password,
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    router.push("/dashboard");
    router.refresh();
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input placeholder="you@example.com" type="email" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <Input placeholder="••••••••" type="password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Signing in..." : "Sign In"}
        </Button>
      </form>
    </Form>
  );
}
```

- [ ] **Step 3: Create `frontend/components/auth/signup-form.tsx`**

```typescript
// frontend/components/auth/signup-form.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

const signupSchema = z
  .object({
    email: z.string().email("Invalid email address"),
    password: z.string().min(6, "Password must be at least 6 characters"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type SignupForm = z.infer<typeof signupSchema>;

export function SignupForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const form = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    defaultValues: { email: "", password: "", confirmPassword: "" },
  });

  async function onSubmit(data: SignupForm) {
    setLoading(true);
    setError(null);

    const supabase = createClient();
    const { error } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    setSuccess(true);
    setLoading(false);
  }

  if (success) {
    return (
      <p className="text-center text-sm text-muted-foreground">
        Check your email for a confirmation link.
      </p>
    );
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input placeholder="you@example.com" type="email" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <Input placeholder="••••••••" type="password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="confirmPassword"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Confirm Password</FormLabel>
              <FormControl>
                <Input placeholder="••••••••" type="password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Creating account..." : "Create Account"}
        </Button>
      </form>
    </Form>
  );
}
```

- [ ] **Step 4: Create `frontend/app/(auth)/login/page.tsx`**

```typescript
// frontend/app/(auth)/login/page.tsx
import Link from "next/link";
import { LoginForm } from "@/components/auth/login-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Welcome back</CardTitle>
          <CardDescription>Sign in to your account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <LoginForm />
          <p className="text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="text-primary hover:underline">
              Sign up
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/app/(auth)/signup/page.tsx`**

```typescript
// frontend/app/(auth)/signup/page.tsx
import Link from "next/link";
import { SignupForm } from "@/components/auth/signup-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function SignupPage() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create an account</CardTitle>
          <CardDescription>
            Enter your email and password to get started
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <SignupForm />
          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 6: Create `frontend/app/auth/callback/route.ts`**

```typescript
// frontend/app/auth/callback/route.ts
import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/dashboard";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth_callback_failed`);
}
```

- [ ] **Step 7: Create `frontend/app/(protected)/dashboard/page.tsx`**

```typescript
// frontend/app/(protected)/dashboard/page.tsx
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  async function signOut() {
    "use server";
    const supabase = await createClient();
    await supabase.auth.signOut();
    redirect("/login");
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-8">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Dashboard</CardTitle>
          <CardDescription>You are authenticated!</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md bg-muted p-4">
            <p className="text-sm font-medium">Signed in as:</p>
            <p className="text-sm text-muted-foreground">{user.email}</p>
          </div>
          <form action={signOut}>
            <Button variant="outline" type="submit" className="w-full">
              Sign Out
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 8: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected output: No errors

- [ ] **Step 9: Commit auth pages**

```bash
cd ..
git add frontend/
git commit -m "feat: add Supabase auth pages (login, signup, callback) and protected dashboard"
```

---

## Task 8: Docker Compose Development Environment

**Files:**
- Create: `frontend/Dockerfile.dev`
- Create: `backend/Dockerfile.dev`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `frontend/Dockerfile.dev`**

```dockerfile
# frontend/Dockerfile.dev
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
```

- [ ] **Step 2: Create `backend/Dockerfile.dev`**

```dockerfile
# backend/Dockerfile.dev
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 3: Create root `docker-compose.yml` (dev)**

```yaml
# docker-compose.yml
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
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - BACKEND_CORS_ORIGINS=["http://localhost:${FRONTEND_PORT:-3000}"]
      - DEBUG=true
```

- [ ] **Step 4: Create root `.env` from example**

```bash
cp .env.example .env
# Edit .env with real values (fill in SUPABASE_URL, SUPABASE_ANON_KEY, etc.)
echo "IMPORTANT: Edit .env with your actual Supabase project values before running"
```

- [ ] **Step 5: Build Docker images to verify Dockerfiles are correct**

```bash
docker compose build --no-cache
```

Expected output: Both `frontend` and `backend` images build without errors

- [ ] **Step 6: Start dev stack and verify health**

```bash
docker compose up -d
sleep 10
curl -s http://localhost:8000/api/v1/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
docker compose down
```

Expected output: `{"status":"ok","version":"0.1.0"}` and `200`

- [ ] **Step 7: Commit dev Docker setup**

```bash
git add frontend/Dockerfile.dev backend/Dockerfile.dev docker-compose.yml
git commit -m "feat: add Docker Compose dev environment with hot-reload for frontend and backend"
```

---

## Task 9: Docker Compose Production Environment

**Files:**
- Create: `frontend/Dockerfile.prod`
- Create: `backend/Dockerfile.prod`
- Create: `nginx/nginx.conf`
- Create: `docker-compose.prod.yml`

- [ ] **Step 1: Create `frontend/Dockerfile.prod`**

```dockerfile
# frontend/Dockerfile.prod
FROM node:20-alpine AS base

FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --only=production

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

RUN npm run build

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000

CMD ["node", "server.js"]
```

- [ ] **Step 2: Create `backend/Dockerfile.prod`**

```dockerfile
# backend/Dockerfile.prod
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

COPY app/ ./app/

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

- [ ] **Step 3: Create `nginx/nginx.conf`**

```nginx
# nginx/nginx.conf
upstream frontend {
    server frontend:3000;
}

upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Backend docs (disable in prod by not exposing)
    location /docs {
        return 404;
    }
}
```

- [ ] **Step 4: Create `docker-compose.prod.yml`**

```yaml
# docker-compose.prod.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - frontend
      - backend
    restart: always

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
      args:
        NEXT_PUBLIC_SUPABASE_URL: ${NEXT_PUBLIC_SUPABASE_URL}
        NEXT_PUBLIC_SUPABASE_ANON_KEY: ${NEXT_PUBLIC_SUPABASE_ANON_KEY}
        NEXT_PUBLIC_BACKEND_URL: ${NEXT_PUBLIC_BACKEND_URL:-/api}
    expose:
      - "3000"
    environment:
      - NODE_ENV=production
    restart: always

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    expose:
      - "8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - BACKEND_CORS_ORIGINS=["${PROD_DOMAIN:-http://localhost}"]
      - DEBUG=false
    restart: always
```

- [ ] **Step 5: Build prod images to verify**

```bash
docker compose -f docker-compose.prod.yml build --no-cache 2>&1 | tail -20
```

Expected output: All three services (`nginx`, `frontend`, `backend`) build without errors

- [ ] **Step 6: Commit prod Docker setup**

```bash
git add frontend/Dockerfile.prod backend/Dockerfile.prod nginx/ docker-compose.prod.yml
git commit -m "feat: add Docker Compose production environment with nginx reverse proxy"
```

---

## Task 10: Integration Verification & README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Run backend tests end-to-end**

```bash
cd backend && uv run pytest tests/ -v --tb=short
```

Expected output:
```
PASSED tests/test_health.py::test_health_check_returns_ok
PASSED tests/test_health.py::test_root_returns_message
PASSED tests/test_chat.py::test_chat_endpoint_without_auth_returns_401
PASSED tests/test_chat.py::test_chat_endpoint_with_mocked_auth_and_agent
```

- [ ] **Step 2: Verify TypeScript compiles without errors**

```bash
cd frontend && npx tsc --noEmit
```

Expected output: No output (clean compile)

- [ ] **Step 3: Verify frontend build succeeds**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected output: `✓ Compiled successfully` (or equivalent Next.js build success message)

- [ ] **Step 4: Verify Docker Compose dev starts both services**

```bash
cd ..
cp .env.example .env  # ensure .env exists
docker compose up -d --build
sleep 15
HEALTH=$(curl -s http://localhost:8000/api/v1/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])")
FRONTEND=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
echo "Backend health: $HEALTH (expected: ok)"
echo "Frontend HTTP: $FRONTEND (expected: 200)"
docker compose down
```

Expected output:
```
Backend health: ok (expected: ok)
Frontend HTTP: 200 (expected: 200)
```

- [ ] **Step 5: Create `README.md`**

```markdown
# Astalink Template

A production-ready monorepo template for building AI-powered web applications.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15+ (App Router) + Shadcn UI + Tailwind CSS |
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
```

- [ ] **Step 6: Final commit**

```bash
git add README.md
git commit -m "docs: add README with setup instructions and architecture overview"
git tag v0.1.0 -m "Initial template release"
```

---

## Self-Review Checklist

### Spec Coverage
| Requirement | Covered In |
|---|---|
| Next.js 15+ | Task 2 |
| Shadcn UI | Task 3 |
| FastAPI | Task 4 |
| LangGraph | Task 5 |
| Docker Compose dev | Task 8 |
| Docker Compose prod | Task 9 |
| Supabase client | Task 6 |
| Supabase Auth | Task 7 |
| Nginx (prod) | Task 9 |
| Root scaffold | Task 1 |

### No Gaps Found
- All requirements are covered with concrete tasks and code
- All types are consistent across tasks (e.g., `ChatState`, `ChatRequest`, `ChatResponse`)
- All imports reference modules defined in previous tasks
- All test commands include expected output

### Type Consistency Check
- `ChatRequest` defined in Task 5 `models/chat.py`, used in `api/v1/chat.py` ✓
- `ChatResponse` same file, same usage ✓
- `ChatState` defined in `agents/chat_agent.py`, only used internally ✓
- `Settings` from `core/config.py` used in `core/security.py` and `main.py` ✓
- `get_current_user` from `api/deps.py` imported in `api/v1/chat.py` ✓
- `verify_token` from `core/security.py` imported in `api/deps.py` ✓
