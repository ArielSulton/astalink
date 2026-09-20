# AstaLink Journey Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace AstaLink's module-oriented shell with a full-stack user-journey experience: a guided home, journey navigation on desktop and mobile, the market terminal at `/market`, resilient backend projections, and responsive primary flows.

**Architecture:** Existing transaction, allocation, portfolio, market, and legal modules remain the sources of truth. A new deterministic journey projection composes those sources into a failure-isolated home response, while one typed frontend navigation contract drives the desktop sidebar and mobile bottom navigation. Migration is incremental: extract the existing terminal first, add the projection and home, then replace the shell and responsive views before removing obsolete code.

**Tech Stack:** FastAPI, Pydantic 2, Supabase/PostgreSQL, pytest, Next.js 16 App Router, React 19, TypeScript 5, Tailwind CSS 4, Base UI, shadcn/ui, Vitest, Testing Library.

**Spec:** `docs/superpowers/specs/2026-09-20-journey-foundation-design.md`

## Global Constraints

- Preserve the current color theme, palette, CSS color tokens, light/dark behavior, and brand identity. Do not modify `frontend/app/globals.css` color declarations.
- Reuse existing Tailwind theme classes such as `bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, `border-border`, `bg-primary`, and `text-chart-*`; do not introduce replacement hex/OKLCH colors.
- Do not expose `Layer 0`, `Layer 1`, agent, graph, optimizer, pipeline, or internal confidence terminology in new user-facing navigation, home copy, or journey DTO labels.
- Keep financial calculations and enforcement in existing domain modules. The journey layer may aggregate, label, order, and assess freshness, but must not recompute domain metrics.
- Treat `None`, empty, stale, and error as different states. Never replace missing or failed financial data with zero.
- Breakpoints are fixed by the spec: mobile `<768`, tablet `768–1023`, desktop `>=1024`.
- The five mobile journey stages are Beranda, Catat, Rencana, Jelajah, and Portofolio. `Tanya Asta` is a separate floating action.
- `/dashboard` becomes the guided home. `/market` becomes the sole canonical market-terminal page.
- Delete unused implementation instead of commenting it out. Compatibility code requires a current consumer and a concrete removal condition.
- Preserve unrelated user changes and stage only files belonging to the current task.

## Review Focus

1. **Missing or unowned workspace:** the API must return auth/ownership errors, while the frontend must show a useful workspace state without calling the home endpoint with an empty ID. Covered by Tasks 4 and 8.
2. **One failed domain source:** home must still return HTTP 200 with successful sections and mark only the failed section as `error`. Covered by Task 3.
3. **Unavailable portfolio price or stale data:** the response must keep the value `null`, expose `empty`/`stale`, and never render `Rp0` as a substitute. Covered by Tasks 2, 3, and 8.
4. **Nested routes and admin visibility:** `/business/:id`, `/allocation/*`, `/approvals/:id`, and admin-only legal routes must activate the correct journey family without weakening backend authorization. Covered by Tasks 5 and 7.
5. **360 px viewport with bottom navigation, floating Asta, forms, and dialogs:** primary content and actions must remain reachable without page-level horizontal overflow or overlap. Covered by Tasks 7, 9, 10, and the final viewport verification in Task 12.

---

## Planned File Structure

### Backend

| File | Responsibility |
| --- | --- |
| `backend/app/models/journey.py` | User-facing journey response models and states |
| `backend/app/core/journey_next_action.py` | Pure, deterministic next-action precedence |
| `backend/app/core/portfolio_read.py` | Shared portfolio read/mark-to-market service reused by portfolio API and home |
| `backend/app/core/journey_home.py` | Domain-source adapter, partial-failure capture, readiness and activity projections |
| `backend/app/api/v1/journey.py` | Authenticated `/journey/home` endpoint |
| `backend/app/api/v1/router.py` | Journey router registration |
| `backend/tests/test_journey_next_action.py` | Next-action rule tests |
| `backend/tests/test_portfolio_read.py` | Shared portfolio reader tests |
| `backend/tests/test_journey_home.py` | Projection, freshness, empty, and partial-failure tests |
| `backend/tests/test_journey_api.py` | Authentication, ownership, and endpoint-schema tests |

### Frontend foundation

| File | Responsibility |
| --- | --- |
| `frontend/vitest.config.ts`, `frontend/vitest.setup.ts` | Frontend unit/component test harness |
| `frontend/lib/journey-navigation.ts` | One typed route-family and navigation contract |
| `frontend/lib/api-client.ts` | Journey DTOs and `getJourneyHome` client |
| `frontend/components/app-shell.tsx` | Shared shell state, approval badge count, and desktop/mobile surfaces |
| `frontend/components/app-sidebar.tsx` | Desktop journey navigation |
| `frontend/components/mobile-navigation.tsx` | Five-stage bottom navigation plus floating Asta action |
| `frontend/components/workspace-switcher.tsx` | Sidebar and compact-header variants using one selection flow |
| `frontend/app/(protected)/layout.tsx` | Providers and the new app shell |

### Frontend pages and focused components

| File | Responsibility |
| --- | --- |
| `frontend/components/terminal/market-terminal.tsx` | Extracted existing terminal behavior |
| `frontend/app/(protected)/market/page.tsx` | Canonical market-terminal route |
| `frontend/app/(protected)/dashboard/page.tsx` | Guided home route |
| `frontend/components/home/*` | Snapshot, next action, readiness, allocation, activity, and section-state views |
| `frontend/components/transactions/transaction-view.tsx` | Desktop table and mobile cards from one transaction model |
| `frontend/components/portfolio/holdings-view.tsx` | Desktop holdings table and mobile holdings cards |
| `frontend/components/ui/responsive-dialog.tsx` | Accessible desktop dialog/mobile bottom sheet primitive |
| Existing journey pages | Responsive padding, subnavigation, copy, and state corrections |

---

### Task 1: Define Journey Models and Deterministic Next-Action Rules

**Files:**
- Create: `backend/app/models/journey.py`
- Create: `backend/app/core/journey_next_action.py`
- Create: `backend/tests/test_journey_next_action.py`

**Interfaces:**
- Consumes: no earlier task interfaces.
- Produces: `SectionState`, `FinancialMetric`, `ReadinessSummary`, `AllocationPreview`, `ActivityItem`, `SectionHealth`, `NextAction`, `JourneyHomeResponse`, `JourneySignals`, and `choose_next_action(signals: JourneySignals) -> NextAction`.

- [ ] **Step 1: Write failing tests for precedence, safety, and fallback**

```python
# backend/tests/test_journey_next_action.py
from app.core.journey_next_action import JourneySignals, choose_next_action


def test_pending_transaction_precedes_every_other_action() -> None:
    action = choose_next_action(JourneySignals(
        pending_transaction_id="txn-1",
        pending_approvals_count=2,
        decisive_gaps=("monthly_expenses",),
        hard_veto_codes=("EMERGENCY_FUND",),
        allocation_available=True,
        allocation_acknowledged=False,
        holdings_count=3,
    ))
    assert action.kind == "resolve_transaction"
    assert action.href == "/chatbot"


def test_decisive_gap_precedes_exploration() -> None:
    action = choose_next_action(JourneySignals(
        decisive_gaps=("horizon_months",), allocation_available=True,
    ))
    assert action.kind == "complete_readiness"
    assert action.href == "/allocation/investor"


def test_empty_sandbox_after_readiness_routes_to_exploration() -> None:
    action = choose_next_action(JourneySignals(
        allocation_available=True, allocation_acknowledged=True, holdings_count=0,
    ))
    assert action.kind == "explore_investments"
    assert action.href == "/recommendations"


def test_neutral_fallback_is_always_available() -> None:
    action = choose_next_action(JourneySignals())
    assert action.kind == "ask_asta"
    assert action.href == "/chatbot"
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `docker compose exec backend pytest tests/test_journey_next_action.py -v`

Expected: FAIL during collection because `app.core.journey_next_action` does not exist.

- [ ] **Step 3: Add explicit user-facing models and states**

```python
# backend/app/models/journey.py
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class SectionState(StrEnum):
    READY = "ready"
    EMPTY = "empty"
    STALE = "stale"
    ERROR = "error"


class FinancialMetric(BaseModel):
    key: Literal["cash_balance", "business_revenue", "portfolio_value"]
    label: str
    value: float | None
    unit: Literal["IDR"] = "IDR"
    state: SectionState
    as_of: datetime | None = None
    source: Literal["workspace", "business_financial_records", "portfolio"]
    change_text: str | None = None


class ReadinessSummary(BaseModel):
    status: Literal["ready", "needs_input", "not_ready", "unavailable"]
    decisive_gaps: list[str] = Field(default_factory=list)
    blocker_codes: list[str] = Field(default_factory=list)
    continuation_href: str = "/allocation"


class AllocationPreview(BaseModel):
    cash: float
    stocks: float
    business: float
    confidence_label: Literal["terbatas", "cukup", "kuat"]
    as_of: datetime
    data_gaps: list[str] = Field(default_factory=list)


class ActivityItem(BaseModel):
    id: str
    kind: Literal["business_transaction", "sandbox_trade", "approval"]
    title: str
    amount: float | None = None
    status: str
    occurred_at: datetime
    href: str


class SectionHealth(BaseModel):
    state: SectionState
    message: str | None = None


class NextAction(BaseModel):
    kind: str
    title: str
    rationale: str
    href: str
    rule_id: str


class JourneyHomeResponse(BaseModel):
    workspace_id: str
    workspace_name: str
    workspace_type: Literal["personal", "business"]
    generated_at: datetime
    financial_snapshot: list[FinancialMetric] = Field(default_factory=list)
    readiness_summary: ReadinessSummary
    next_action: NextAction
    allocation_preview: AllocationPreview | None = None
    recent_activity: list[ActivityItem] = Field(default_factory=list)
    pending_approvals_count: int = 0
    section_health: dict[str, SectionHealth] = Field(default_factory=dict)
```

- [ ] **Step 4: Implement the pure next-action composer**

```python
# backend/app/core/journey_next_action.py
from dataclasses import dataclass

from app.models.journey import NextAction


@dataclass(frozen=True)
class JourneySignals:
    pending_transaction_id: str | None = None
    pending_approvals_count: int = 0
    decisive_gaps: tuple[str, ...] = ()
    hard_veto_codes: tuple[str, ...] = ()
    allocation_available: bool = False
    allocation_acknowledged: bool = False
    holdings_count: int = 0


def choose_next_action(signals: JourneySignals) -> NextAction:
    if signals.pending_transaction_id:
        return NextAction(kind="resolve_transaction", title="Konfirmasi transaksi tertunda",
            rationale="Selesaikan pencatatan agar ringkasan keuangan tetap akurat.",
            href="/chatbot", rule_id="pending_transaction")
    if signals.pending_approvals_count:
        return NextAction(kind="review_approval", title="Tinjau persetujuan yang menunggu",
            rationale="Ada keputusan yang membutuhkan tindakanmu.",
            href="/approvals", rule_id="pending_approval")
    if signals.decisive_gaps:
        return NextAction(kind="complete_readiness", title="Lengkapi kesiapan finansial",
            rationale="Beberapa informasi penting masih menentukan arah dana.",
            href="/allocation/investor", rule_id="decisive_gap")
    if signals.hard_veto_codes:
        return NextAction(kind="address_readiness", title="Amankan kondisi dasar terlebih dahulu",
            rationale="Ada batas kesiapan yang perlu diselesaikan sebelum menambah investasi.",
            href="/allocation", rule_id="readiness_blocker")
    if signals.allocation_available and not signals.allocation_acknowledged:
        return NextAction(kind="review_allocation", title="Tinjau rencana dan pembagian dana",
            rationale="Rencana terbaru sudah tersedia untuk diperiksa.",
            href="/allocation", rule_id="unreviewed_allocation")
    if signals.allocation_available and signals.holdings_count == 0:
        return NextAction(kind="explore_investments", title="Eksplorasi pilihan investasi",
            rationale="Kondisimu sudah cukup untuk mulai membandingkan pilihan.",
            href="/recommendations", rule_id="ready_empty_portfolio")
    if signals.holdings_count:
        return NextAction(kind="review_portfolio", title="Tinjau perkembangan portofolio",
            rationale="Lihat perubahan nilai dan kesesuaian bobot investasimu.",
            href="/portfolio", rule_id="existing_holdings")
    return NextAction(kind="ask_asta", title="Mulai dari kondisi keuanganmu",
        rationale="Asta dapat membantu menentukan langkah yang paling relevan.",
        href="/chatbot", rule_id="neutral_fallback")
```

- [ ] **Step 5: Run tests and commit**

Run: `docker compose exec backend pytest tests/test_journey_next_action.py -v`

Expected: all tests PASS.

```bash
git add backend/app/models/journey.py backend/app/core/journey_next_action.py backend/tests/test_journey_next_action.py
git commit -m "feat(journey): define home models and next actions"
```

### Task 2: Extract a Shared Portfolio Read Service

**Files:**
- Create: `backend/app/core/portfolio_read.py`
- Create: `backend/tests/test_portfolio_read.py`
- Modify: `backend/app/api/v1/portfolio.py:1-112`
- Modify: `backend/tests/test_portfolio_api.py`

**Interfaces:**
- Consumes: `PortfolioResponse` and `HoldingView` from `app.models.portfolio`.
- Produces: `fetch_last_price(ticker: str) -> float | None` and `build_portfolio(sb, workspace_id: str, price_loader: Callable | None = None) -> PortfolioResponse`.

- [ ] **Step 1: Write failing service tests for marked and unpriced holdings**

```python
# backend/tests/test_portfolio_read.py
from unittest.mock import MagicMock

from app.core.portfolio_read import build_portfolio


def _admin() -> MagicMock:
    admin = MagicMock()
    holdings = MagicMock()
    holdings.select.return_value.eq.return_value.execute.return_value.data = [
        {"ticker": "BBCA", "quantity": 100, "avg_cost": 9000},
    ]
    transactions = MagicMock()
    transactions.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    workspaces = MagicMock()
    workspaces.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"cash_balance": 500_000},
    ]
    admin.table.side_effect = lambda name: {
        "holdings": holdings, "transactions": transactions, "workspaces": workspaces,
    }[name]
    return admin


def test_build_portfolio_marks_holdings_to_market() -> None:
    result = build_portfolio(_admin(), "ws-1", price_loader=lambda _: 10_000)
    assert result.total_market_value == 1_000_000
    assert result.total_equity == 1_500_000


def test_build_portfolio_keeps_unavailable_price_null() -> None:
    result = build_portfolio(_admin(), "ws-1", price_loader=lambda _: None)
    assert result.holdings[0].market_value is None
    assert result.total_market_value is None
    assert result.total_equity is None
```

- [ ] **Step 2: Run the test and verify the missing module failure**

Run: `docker compose exec backend pytest tests/test_portfolio_read.py -v`

Expected: FAIL because `app.core.portfolio_read` does not exist.

- [ ] **Step 3: Move read logic without changing semantics**

```python
# backend/app/core/portfolio_read.py
from collections.abc import Callable

from app.core.wallet import get_workspace_balance
from app.models.portfolio import HoldingView, PortfolioResponse

PriceLoader = Callable[[str], float | None]


def fetch_last_price(ticker: str) -> float | None:
    try:
        from app.agents.market.yfinance_client import fetch_price_series_with_indicators
        return fetch_price_series_with_indicators(ticker).get("last_close")
    except Exception:
        return None


def build_portfolio(sb, workspace_id: str, price_loader: PriceLoader | None = None) -> PortfolioResponse:
    load_price = price_loader or fetch_last_price
    rows = (sb.table("holdings").select("*").eq("workspace_id", workspace_id).execute().data) or []
    holdings: list[HoldingView] = []
    total_market_value = 0.0
    total_unrealized = 0.0
    any_priced = False
    for row in rows:
        quantity = float(row["quantity"])
        average = float(row["avg_cost"])
        cost_basis = quantity * average
        price = load_price(row["ticker"])
        market_value = unrealized = unrealized_pct = None
        if price is not None:
            any_priced = True
            market_value = quantity * price
            unrealized = market_value - cost_basis
            unrealized_pct = unrealized / cost_basis if cost_basis else None
            total_market_value += market_value
            total_unrealized += unrealized
        holdings.append(HoldingView(ticker=row["ticker"], quantity=quantity,
            avg_cost=average, cost_basis=cost_basis, last_price=price,
            market_value=market_value, unrealized_pnl=unrealized,
            unrealized_pnl_pct=unrealized_pct))
    cash = get_workspace_balance(sb, workspace_id) or 0.0
    realized_rows = (sb.table("transactions").select("realized_pnl")
        .eq("workspace_id", workspace_id).eq("side", "sell").execute().data) or []
    realized = sum(float(row["realized_pnl"]) for row in realized_rows
                   if row.get("realized_pnl") is not None)
    return PortfolioResponse(workspace_id=workspace_id, cash_balance=cash,
        holdings=holdings, total_market_value=total_market_value if any_priced else None,
        total_unrealized_pnl=total_unrealized if any_priced else None,
        total_realized_pnl=realized,
        total_equity=(cash + total_market_value) if any_priced else None)
```

- [ ] **Step 4: Make the portfolio endpoint delegate to the service**

```python
# backend/app/api/v1/portfolio.py
from app.core.portfolio_read import build_portfolio, fetch_last_price

# Delete the old _last_price and get_portfolio calculation body.
@router.get("", response_model=PortfolioResponse)
async def get_portfolio(workspace_id: str, user: dict = Depends(get_current_user)) -> PortfolioResponse:
    sb = get_admin_client()
    assert_workspace_owned(sb, workspace_id, user["sub"])
    return build_portfolio(sb, workspace_id)

# Buy/sell paths call fetch_last_price(ticker) instead of _last_price(ticker).
```

Update `backend/tests/test_portfolio_api.py` patches from `app.api.v1.portfolio._last_price` to `app.api.v1.portfolio.fetch_last_price` for buy/sell tests. The GET endpoint tests should patch `app.api.v1.portfolio.build_portfolio` or exercise the new service directly, not duplicate its calculations.

- [ ] **Step 5: Run portfolio tests and commit**

Run: `docker compose exec backend pytest tests/test_portfolio_read.py tests/test_portfolio_api.py -v`

Expected: all tests PASS, including the existing null-not-zero assertion.

```bash
git add backend/app/core/portfolio_read.py backend/app/api/v1/portfolio.py backend/tests/test_portfolio_read.py backend/tests/test_portfolio_api.py
git commit -m "refactor(portfolio): share read projection"
```

### Task 3: Build the Failure-Isolated Home Projection

**Files:**
- Create: `backend/app/core/journey_home.py`
- Create: `backend/tests/test_journey_home.py`

**Interfaces:**
- Consumes: Task 1 journey models and next-action composer; Task 2 `build_portfolio`; existing `InvestorProfile`, `evaluate_constraints`, Supabase tables, and confirmed ledgers.
- Produces: `SupabaseJourneySource(sb, workspace_id, user_id)` and `build_journey_home(source, now: datetime | None = None) -> JourneyHomeResponse`.

- [ ] **Step 1: Write a fake source and failing composition tests**

```python
# backend/tests/test_journey_home.py
from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.core.journey_home import build_journey_home
from app.models.portfolio import PortfolioResponse


NOW = datetime(2026, 9, 20, 3, 30, tzinfo=UTC)


def _source() -> MagicMock:
    source = MagicMock()
    source.load_workspace.return_value = {"id": "ws-1", "name": "Personal", "type": "personal", "cash_balance": 10_000_000}
    source.load_business_summary.return_value = {"value": 2_000_000, "as_of": NOW}
    source.load_portfolio.return_value = PortfolioResponse(workspace_id="ws-1", cash_balance=10_000_000, holdings=[])
    source.load_readiness.return_value = {"status": "needs_input", "gaps": ["monthly_expenses"], "blockers": []}
    source.load_allocation_preview.return_value = None
    source.load_recent_activity.return_value = []
    source.load_pending.return_value = {"transaction_id": None, "approvals": 0}
    return source


def test_home_keeps_successful_sections_when_portfolio_fails() -> None:
    source = _source()
    source.load_portfolio.side_effect = RuntimeError("market timeout")
    result = build_journey_home(source, now=NOW)
    cash = next(metric for metric in result.financial_snapshot if metric.key == "cash_balance")
    portfolio = next(metric for metric in result.financial_snapshot if metric.key == "portfolio_value")
    assert cash.value == 10_000_000
    assert portfolio.value is None
    assert portfolio.state == "error"
    assert result.section_health["portfolio"].state == "error"


def test_unpriced_portfolio_is_empty_not_zero() -> None:
    source = _source()
    source.load_portfolio.return_value = PortfolioResponse(
        workspace_id="ws-1", cash_balance=10_000_000,
        holdings=[], total_market_value=None, total_equity=None,
    )
    result = build_journey_home(source, now=NOW)
    metric = next(item for item in result.financial_snapshot if item.key == "portfolio_value")
    assert metric.value is None
    assert metric.state == "empty"


def test_home_uses_decisive_gaps_for_next_action() -> None:
    result = build_journey_home(_source(), now=NOW)
    assert result.next_action.kind == "complete_readiness"


def test_home_keeps_stale_business_value_and_timestamp() -> None:
    source = _source()
    stale_at = NOW - timedelta(days=32)
    source.load_business_summary.return_value = {"value": 2_000_000, "as_of": stale_at}
    result = build_journey_home(source, now=NOW)
    metric = next(item for item in result.financial_snapshot if item.key == "business_revenue")
    assert metric.value == 2_000_000
    assert metric.as_of == stale_at
    assert metric.state == "stale"
    assert result.section_health["business"].state == "stale"
```

Add `timedelta` to the datetime import used by this test.

- [ ] **Step 2: Run tests and confirm the module is missing**

Run: `docker compose exec backend pytest tests/test_journey_home.py -v`

Expected: FAIL because `app.core.journey_home` does not exist.

- [ ] **Step 3: Implement source queries with explicit domain ownership**

```python
# backend/app/core/journey_home.py (source shape)
class SupabaseJourneySource:
    def __init__(self, sb, workspace_id: str, user_id: str) -> None:
        self.sb = sb
        self.workspace_id = workspace_id
        self.user_id = user_id

    def load_workspace(self) -> dict:
        rows = (self.sb.table("workspaces").select("id,name,type,cash_balance")
                .eq("id", self.workspace_id).limit(1).execute().data) or []
        if not rows:
            raise LookupError("workspace missing after ownership check")
        return rows[0]

    def load_portfolio(self):
        return build_portfolio(self.sb, self.workspace_id)

    def load_readiness(self) -> dict:
        rows = (self.sb.table("investor_profiles").select("profile")
                .eq("workspace_id", self.workspace_id).limit(1).execute().data) or []
        investor = InvestorProfile.model_validate((rows[0] if rows else {}).get("profile") or {})
        decisive = ("monthly_expenses", "emergency_fund", "capital_is_borrowed", "horizon_months")
        gaps = [name for name in decisive if getattr(investor, name) is None]
        constraints = evaluate_constraints(investor)
        status = "needs_input" if gaps else "not_ready" if constraints.veto_flags else "ready"
        return {"status": status, "gaps": gaps,
                "blockers": [flag.code for flag in constraints.veto_flags if flag.hard]}
```

Implement the remaining source methods with these exact reads:

```text
load_business_summary:
  businesses.select("id").eq("workspace_id", workspace_id)
  business_financial_records.select("omset,period_year,created_at").in_("business_id", ids).eq("period_year", current_year)
  business_transactions.select("confirmed_at").in_("business_id", ids).eq("status", "confirmed").order("confirmed_at", desc=True).limit(1)

load_pending:
  business_transactions.select("id").in_("business_id", ids).eq("status", "pending_confirmation").order("created_at", desc=True).limit(1)
  audit_log.select("audit_id").eq("workspace_id", workspace_id).eq("user_id", user_id).eq("status", "awaiting_approval")

load_allocation_preview:
  chat_conversations.select("id").eq("workspace_id", workspace_id).eq("user_id", user_id).order("updated_at", desc=True)
  chat_messages.select("metadata,created_at").in_("conversation_id", ids).eq("role", "assistant").order("created_at", desc=True).limit(20)
  choose the first metadata.layer0_result with a non-null allocation; map LOW/MEDIUM/HIGH to terbatas/cukup/kuat

load_recent_activity:
  latest confirmed business_transactions through owned business ids
  latest transactions by workspace_id
  awaiting audit_log rows by workspace_id and user_id
  normalize, merge, sort occurred_at descending, return at most 6 ActivityItem values
```

- [ ] **Step 4: Compose sections independently and never fabricate zero**

```python
# backend/app/core/journey_home.py (composition skeleton)
def build_journey_home(source, now: datetime | None = None) -> JourneyHomeResponse:
    generated_at = now or datetime.now(UTC)
    workspace = source.load_workspace()  # critical: allowed to raise
    health: dict[str, SectionHealth] = {}

    def capture(name: str, loader, fallback):
        try:
            value = loader()
            health[name] = SectionHealth(state=SectionState.READY)
            return value
        except Exception:
            log.exception("journey_home: %s load failed", name)
            health[name] = SectionHealth(state=SectionState.ERROR,
                message="Bagian ini belum dapat diperbarui.")
            return fallback

    business = capture("business", source.load_business_summary, None)
    portfolio = capture("portfolio", source.load_portfolio, None)
    readiness = capture("readiness", source.load_readiness,
        {"status": "unavailable", "gaps": [], "blockers": []})
    allocation = capture("allocation", source.load_allocation_preview, None)
    activity = capture("activity", source.load_recent_activity, [])
    pending = capture("pending", source.load_pending,
        {"transaction_id": None, "approvals": 0})

    business_state = health["business"].state
    if business_state != SectionState.ERROR:
        business_state = (SectionState.EMPTY if business is None else
            SectionState.STALE if generated_at - business["as_of"] > timedelta(days=31)
            else SectionState.READY)
        health["business"] = SectionHealth(state=business_state)
    portfolio_state = health["portfolio"].state
    if portfolio_state != SectionState.ERROR:
        portfolio_state = (SectionState.EMPTY
            if portfolio is None or portfolio.total_market_value is None
            else SectionState.READY)
        health["portfolio"] = SectionHealth(state=portfolio_state)
    allocation_state = health["allocation"].state
    if allocation_state != SectionState.ERROR:
        allocation_state = (SectionState.EMPTY if allocation is None else
            SectionState.STALE if generated_at - allocation.as_of > timedelta(days=7)
            else SectionState.READY)
        health["allocation"] = SectionHealth(state=allocation_state)
    if health["activity"].state != SectionState.ERROR and not activity:
        health["activity"] = SectionHealth(state=SectionState.EMPTY)

    metrics = [FinancialMetric(key="cash_balance", label="Kas tersedia",
        value=float(workspace["cash_balance"]), state=SectionState.READY,
        as_of=generated_at, source="workspace")]
    metrics.append(FinancialMetric(key="business_revenue", label="Omset tahun ini",
        value=business["value"] if business else None,
        state=business_state,
        as_of=business["as_of"] if business else None,
        source="business_financial_records"))
    metrics.append(FinancialMetric(key="portfolio_value", label="Portofolio sandbox",
        value=portfolio.total_market_value if portfolio else None,
        state=portfolio_state,
        as_of=generated_at if portfolio else None, source="portfolio"))
    signals = JourneySignals(pending_transaction_id=pending["transaction_id"],
        pending_approvals_count=pending["approvals"],
        decisive_gaps=tuple(readiness["gaps"]),
        hard_veto_codes=tuple(readiness["blockers"]),
        allocation_available=allocation is not None,
        allocation_acknowledged=False,
        holdings_count=len(portfolio.holdings) if portfolio else 0)
    return JourneyHomeResponse(workspace_id=workspace["id"],
        workspace_name=workspace["name"], workspace_type=workspace["type"],
        generated_at=generated_at, financial_snapshot=metrics,
        readiness_summary=ReadinessSummary(status=readiness["status"],
            decisive_gaps=readiness["gaps"], blocker_codes=readiness["blockers"]),
        next_action=choose_next_action(signals), allocation_preview=allocation,
        recent_activity=activity, pending_approvals_count=pending["approvals"],
        section_health=health)
```

Add `timedelta` to the implementation's datetime imports. Use the explicit thresholds shown above: business summaries become stale after 31 days and allocation previews after 7 days. Stale values remain visible with their original `as_of`; they are never replaced with zero. A successfully loaded but absent value is `empty`, while exceptions remain `error` with the safe fallback message.

- [ ] **Step 5: Run projection tests and commit**

Run: `docker compose exec backend pytest tests/test_journey_home.py tests/test_journey_next_action.py tests/test_portfolio_read.py -v`

Expected: all tests PASS.

```bash
git add backend/app/core/journey_home.py backend/tests/test_journey_home.py
git commit -m "feat(journey): compose resilient home projection"
```

### Task 4: Expose the Authenticated Journey Home API

**Files:**
- Create: `backend/app/api/v1/journey.py`
- Create: `backend/tests/test_journey_api.py`
- Modify: `backend/app/api/v1/router.py`

**Interfaces:**
- Consumes: Task 3 `SupabaseJourneySource` and `build_journey_home`.
- Produces: `GET /api/v1/journey/home?workspace_id=<uuid>` returning `JourneyHomeResponse`.

- [ ] **Step 1: Write auth, ownership, and success tests**

```python
# backend/tests/test_journey_api.py
import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.models.journey import JourneyHomeResponse, NextAction, ReadinessSummary


def test_journey_home_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/journey/home?workspace_id=ws-1").status_code == 401


def test_journey_home_rejects_unowned_workspace(client: TestClient) -> None:
    with patch("app.api.deps.verify_token", return_value={"sub": str(uuid.uuid4())}), \
         patch("app.api.v1.journey.assert_workspace_owned", side_effect=__import__("fastapi").HTTPException(403, "forbidden")):
        response = client.get("/api/v1/journey/home?workspace_id=ws-1",
            headers={"Authorization": "Bearer x"})
    assert response.status_code == 403


def test_journey_home_returns_projection(client: TestClient) -> None:
    payload = JourneyHomeResponse(workspace_id="ws-1", workspace_name="Personal",
        workspace_type="personal", generated_at="2026-09-20T03:30:00Z",
        readiness_summary=ReadinessSummary(status="needs_input"),
        next_action=NextAction(kind="ask_asta", title="Mulai", rationale="Mulai", href="/chatbot", rule_id="fallback"))
    with patch("app.api.deps.verify_token", return_value={"sub": str(uuid.uuid4())}), \
         patch("app.api.v1.journey.assert_workspace_owned"), \
         patch("app.api.v1.journey.build_journey_home", return_value=payload):
        response = client.get("/api/v1/journey/home?workspace_id=ws-1",
            headers={"Authorization": "Bearer x"})
    assert response.status_code == 200
    assert response.json()["next_action"]["kind"] == "ask_asta"
```

- [ ] **Step 2: Run tests and verify the route is missing**

Run: `docker compose exec backend pytest tests/test_journey_api.py -v`

Expected: FAIL with 404 or import failure.

- [ ] **Step 3: Add the endpoint and router registration**

```python
# backend/app/api/v1/journey.py
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.journey_home import SupabaseJourneySource, build_journey_home
from app.core.ownership import assert_workspace_owned
from app.core.supabase_admin import get_admin_client
from app.models.journey import JourneyHomeResponse

router = APIRouter()


@router.get("/home", response_model=JourneyHomeResponse)
async def get_journey_home(workspace_id: str, user: dict = Depends(get_current_user)) -> JourneyHomeResponse:
    sb = get_admin_client()
    assert_workspace_owned(sb, workspace_id, user["sub"])
    return build_journey_home(SupabaseJourneySource(sb, workspace_id, user["sub"]))
```

```python
# backend/app/api/v1/router.py
from app.api.v1 import agent, allocation, auth, business, chat, health, journey, legal, market

api_router.include_router(journey.router, prefix="/journey", tags=["journey"])
```

- [ ] **Step 4: Run API and regression tests**

Run: `docker compose exec backend pytest tests/test_journey_api.py tests/test_journey_home.py tests/test_portfolio_api.py tests/test_business_api.py tests/test_approvals_endpoint.py -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/journey.py backend/app/api/v1/router.py backend/tests/test_journey_api.py
git commit -m "feat(api): expose journey home summary"
```

### Task 5: Add Frontend Tests and One Typed Navigation Contract

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`
- Create: `frontend/lib/journey-navigation.ts`
- Create: `frontend/lib/journey-navigation.test.ts`

**Interfaces:**
- Consumes: the approved route map from the spec.
- Produces: `DESKTOP_SECTIONS`, `MOBILE_TABS`, `isJourneyRouteActive(pathname, prefixes)`, and `visibleDesktopSections(isAdmin)`.

- [ ] **Step 1: Install the focused frontend test harness**

Run from `frontend/`:

```bash
npm install --save-dev vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom
```

Add scripts:

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

- [ ] **Step 2: Configure Vitest with the existing `@` alias**

```typescript
// frontend/vitest.config.ts
import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, ".") } },
  test: { environment: "jsdom", setupFiles: ["./vitest.setup.ts"] },
});
```

```typescript
// frontend/vitest.setup.ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 3: Write failing navigation-contract tests**

```typescript
// frontend/lib/journey-navigation.test.ts
import { describe, expect, it } from "vitest";
import { MOBILE_TABS, isJourneyRouteActive, visibleDesktopSections } from "./journey-navigation";

describe("journey navigation", () => {
  it("activates nested route families", () => {
    expect(isJourneyRouteActive("/business/abc", ["/transactions", "/business"])).toBe(true);
    expect(isJourneyRouteActive("/allocation/intake/abc", ["/allocation"])).toBe(true);
    expect(isJourneyRouteActive("/approvals/a1", ["/portfolio", "/approvals"])).toBe(true);
  });

  it("does not confuse similarly-prefixed routes", () => {
    expect(isJourneyRouteActive("/portfolio-old", ["/portfolio"])).toBe(false);
  });

  it("keeps exactly five mobile journey stages", () => {
    expect(MOBILE_TABS.map((tab) => tab.label)).toEqual([
      "Beranda", "Catat", "Rencana", "Jelajah", "Portofolio",
    ]);
  });

  it("hides regulatory documents from non-admin users", () => {
    expect(JSON.stringify(visibleDesktopSections(false))).not.toContain("/legal-docs");
    expect(JSON.stringify(visibleDesktopSections(true))).toContain("/legal-docs");
  });
});
```

- [ ] **Step 4: Run the test and verify the contract is missing**

Run: `npm test -- lib/journey-navigation.test.ts`

Expected: FAIL because `journey-navigation.ts` does not exist.

- [ ] **Step 5: Implement one shared typed configuration**

```typescript
// frontend/lib/journey-navigation.ts
import { Bot, Building2, ChartCandlestick, ClipboardCheck, House, Lightbulb,
  Newspaper, PieChart, Receipt, Scale, Settings, Wallet, type LucideIcon } from "lucide-react";

export type JourneyItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  activePrefixes: string[];
  adminOnly?: boolean;
};

export type JourneySection = { label: string; items: JourneyItem[] };

export const ASTA_ACTION: JourneyItem = {
  href: "/chatbot", label: "Tanya Asta", icon: Bot, activePrefixes: ["/chatbot"],
};

export const DESKTOP_SECTIONS: JourneySection[] = [
  { label: "", items: [{ href: "/dashboard", label: "Beranda", icon: House, activePrefixes: ["/dashboard"] }] },
  { label: "Catat & Kelola", items: [
    { href: "/transactions", label: "Transaksi", icon: Receipt, activePrefixes: ["/transactions"] },
    { href: "/business", label: "Bisnis Saya", icon: Building2, activePrefixes: ["/business"] },
  ]},
  { label: "Rencanakan", items: [
    { href: "/allocation", label: "Rencana Dana", icon: PieChart, activePrefixes: ["/allocation"] },
  ]},
  { label: "Eksplorasi", items: [
    { href: "/recommendations", label: "Ide Investasi", icon: Lightbulb, activePrefixes: ["/recommendations"] },
    { href: "/market", label: "Pasar & Grafik", icon: ChartCandlestick, activePrefixes: ["/market"] },
    { href: "/news", label: "Berita Pasar", icon: Newspaper, activePrefixes: ["/news"] },
  ]},
  { label: "Portofolio", items: [
    { href: "/portfolio", label: "Kepemilikan & Kinerja", icon: Wallet, activePrefixes: ["/portfolio"] },
    { href: "/approvals", label: "Persetujuan", icon: ClipboardCheck, activePrefixes: ["/approvals"] },
  ]},
  { label: "", items: [
    { href: "/settings", label: "Pengaturan", icon: Settings, activePrefixes: ["/settings"] },
    { href: "/legal-docs", label: "Dokumen Regulasi", icon: Scale, activePrefixes: ["/legal-docs"], adminOnly: true },
  ]},
];

export const MOBILE_TABS: JourneyItem[] = [
  { href: "/dashboard", label: "Beranda", icon: House, activePrefixes: ["/dashboard"] },
  { href: "/transactions", label: "Catat", icon: Receipt, activePrefixes: ["/transactions", "/business"] },
  { href: "/allocation", label: "Rencana", icon: PieChart, activePrefixes: ["/allocation"] },
  { href: "/recommendations", label: "Jelajah", icon: Lightbulb, activePrefixes: ["/recommendations", "/market", "/news"] },
  { href: "/portfolio", label: "Portofolio", icon: Wallet, activePrefixes: ["/portfolio", "/approvals"] },
];

export function isJourneyRouteActive(pathname: string, prefixes: string[]): boolean {
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export function visibleDesktopSections(isAdmin: boolean): JourneySection[] {
  return DESKTOP_SECTIONS.map((section) => ({
    ...section, items: section.items.filter((item) => !item.adminOnly || isAdmin),
  })).filter((section) => section.items.length > 0);
}
```

- [ ] **Step 6: Run tests, type-check, and commit**

Run: `npm test -- lib/journey-navigation.test.ts`

Run: `npx tsc --noEmit`

Expected: both PASS.

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/vitest.setup.ts frontend/lib/journey-navigation.ts frontend/lib/journey-navigation.test.ts
git commit -m "test(frontend): add journey navigation contract"
```

### Task 6: Extract the Market Terminal and Establish `/market`

**Files:**
- Create: `frontend/components/terminal/market-terminal.tsx`
- Create: `frontend/app/(protected)/market/page.tsx`
- Modify: `frontend/components/terminal/index.ts`
- Modify: `frontend/app/(protected)/dashboard/page.tsx`
- Create: `frontend/components/terminal/market-terminal.test.tsx`

**Interfaces:**
- Consumes: existing terminal components and hooks unchanged.
- Produces: `MarketTerminal` and canonical `/market` route. `/dashboard` temporarily renders the same extracted component until Task 8 replaces it.

- [ ] **Step 1: Write a failing smoke test for the extracted view**

```typescript
// frontend/components/terminal/market-terminal.test.tsx
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { MarketTerminal } from "./market-terminal";

vi.mock("@/components/workspace-context", () => ({ useWorkspace: () => ({ workspaceId: null }) }));
vi.mock("@/lib/supabase/client", () => ({ createClient: () => ({ auth: { getSession: async () => ({ data: { session: null } }) } }) }));

test("renders the market terminal heading", () => {
  render(<MarketTerminal />);
  expect(screen.getByText(/pasar/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test and verify the component is missing**

Run: `npm test -- components/terminal/market-terminal.test.tsx`

Expected: FAIL because `market-terminal.tsx` does not exist.

- [ ] **Step 3: Move the dashboard terminal code into one component**

Create `frontend/components/terminal/market-terminal.tsx` by moving the complete contents of the current `dashboard/page.tsx` into that file, then make only these mechanical edits:

- keep the existing `"use client"` directive and imports required by the terminal;
- rename `export default function DashboardPage()` to `export function MarketTerminal()`;
- keep `DEFAULT_WATCHLIST`, every market/workspace state variable, all existing effects, `subplots`, and the full live terminal JSX;
- remove the commented portfolio-strip block and remove `MiniStat`, `fmtIdr`, `fmtSigned`, `Link`, `ArrowRight`, `LineChart`, and `PortfolioResponse` when they become unused;
- keep the current `TerminalHeader`, `WatchlistSidebar`, `ChartToolbar`, `MainChartArea`, `SubplotTabs`, and `BusinessConditionPanel` prop wiring byte-for-byte unless an import path must change.

During the move, delete the commented-out portfolio strip, `MiniStat`, its unused `LineChart`, `ArrowRight`, and `Link` imports. Do not preserve that dead block in comments.

- [ ] **Step 4: Mount the same component at both routes during migration**

```tsx
// frontend/app/(protected)/market/page.tsx
import { MarketTerminal } from "@/components/terminal/market-terminal";
export default function MarketPage() { return <MarketTerminal />; }
```

```tsx
// frontend/app/(protected)/dashboard/page.tsx (temporary until Task 8)
import { MarketTerminal } from "@/components/terminal/market-terminal";
export default function DashboardPage() { return <MarketTerminal />; }
```

- [ ] **Step 5: Run tests and static checks, then commit**

Run: `npm test -- components/terminal/market-terminal.test.tsx`

Run: `npx tsc --noEmit`

Run: `npm run lint -- components/terminal/market-terminal.tsx app/\(protected\)/market/page.tsx app/\(protected\)/dashboard/page.tsx`

Expected: all PASS.

```bash
git add frontend/components/terminal frontend/app/\(protected\)/market frontend/app/\(protected\)/dashboard/page.tsx
git commit -m "refactor(market): move terminal to canonical view"
```

### Task 7: Replace the Application Shell with Journey Navigation

**Files:**
- Create: `frontend/components/app-shell.tsx`
- Create: `frontend/components/mobile-navigation.tsx`
- Create: `frontend/components/mobile-navigation.test.tsx`
- Modify: `frontend/components/app-sidebar.tsx`
- Modify: `frontend/components/workspace-switcher.tsx`
- Modify: `frontend/components/ui/sidebar.tsx`
- Modify: `frontend/app/(protected)/layout.tsx`
- Modify: `frontend/hooks/use-mobile.ts`

**Interfaces:**
- Consumes: Task 5 navigation contract and existing `WorkspaceProvider`.
- Produces: `AppShell({ children })`, `MobileNavigation`, desktop `AppSidebar({ pendingApprovals })`, and workspace switcher variants.

- [ ] **Step 1: Write failing mobile-navigation tests for route state and safe-area placement**

```typescript
// frontend/components/mobile-navigation.test.tsx
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { MobileNavigation } from "./mobile-navigation";

vi.mock("next/navigation", () => ({ usePathname: () => "/allocation/intake/biz-1" }));

test("renders five stages and a separate Asta action", () => {
  render(<MobileNavigation pendingApprovals={0} />);
  expect(screen.getAllByRole("link").filter((node) => node.closest("nav"))).toHaveLength(5);
  expect(screen.getByRole("link", { name: "Tanya Asta" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Rencana" })).toHaveAttribute("aria-current", "page");
});

test("pins navigation and Asta above the safe area", () => {
  const { container } = render(<MobileNavigation pendingApprovals={0} />);
  expect(container.querySelector("nav")).toHaveClass("fixed", "bottom-0", "lg:hidden");
  expect(screen.getByRole("link", { name: "Tanya Asta" }).className).toContain("env(safe-area-inset-bottom)");
});
```

- [ ] **Step 2: Run the test and verify the component is missing**

Run: `npm test -- components/mobile-navigation.test.tsx`

Expected: FAIL because `mobile-navigation.tsx` does not exist.

- [ ] **Step 3: Implement the five-stage bottom navigation and floating Asta action**

```tsx
// frontend/components/mobile-navigation.tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot } from "lucide-react";
import { MOBILE_TABS, isJourneyRouteActive } from "@/lib/journey-navigation";

export function MobileNavigation({ pendingApprovals }: { pendingApprovals: number }) {
  const pathname = usePathname();
  return (
    <>
      <Link aria-label="Tanya Asta" href="/chatbot"
        className="fixed right-4 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-40 inline-flex min-h-11 items-center gap-2 rounded-full bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-lg lg:hidden">
        <Bot className="size-4" /> Tanya Asta
      </Link>
      <nav aria-label="Perjalanan utama"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-border bg-card pb-[env(safe-area-inset-bottom)] lg:hidden">
        {MOBILE_TABS.map((tab) => {
          const active = isJourneyRouteActive(pathname, tab.activePrefixes);
          return <Link key={tab.href} href={tab.href} aria-current={active ? "page" : undefined}
            className="relative flex min-h-16 flex-col items-center justify-center gap-1 text-[10px] text-muted-foreground aria-[current=page]:text-primary">
            <tab.icon className="size-5" /><span>{tab.label}</span>
            {tab.label === "Portofolio" && pendingApprovals > 0 && <span className="absolute right-3 top-2 rounded-full bg-destructive px-1 text-[9px] text-white">{pendingApprovals}</span>}
          </Link>;
        })}
      </nav>
    </>
  );
}
```

- [ ] **Step 4: Refactor the sidebar to consume the shared configuration**

Replace `NAV_SECTIONS`, `NavLeaf`, `NavGroup`, the `/business/detail` special case, and old historical comments with imports of `ASTA_ACTION`, `visibleDesktopSections`, and `isJourneyRouteActive`. Change the component signature to:

```tsx
export function AppSidebar({ pendingApprovals = 0, ...props }: React.ComponentProps<typeof Sidebar> & {
  pendingApprovals?: number;
}) {
```

Preserve the current fail-closed `getMe` admin check. Immediately after `<SidebarHeader>`, render `ASTA_ACTION` as the first `SidebarMenuButton`. Then map `visibleDesktopSections(isAdmin)` to `SidebarGroup` elements and map every item to a direct `SidebarMenuButton`; its `isActive` value must be `isJourneyRouteActive(pathname, item.activePrefixes)`. For the `/approvals` item, render a visible badge with `pendingApprovals` only when the count is greater than zero. Keep `NavUser` in the footer and delete all expand/collapse group state and imports.

- [ ] **Step 5: Add a client app shell and compact workspace header**

```tsx
// frontend/components/app-shell.tsx
"use client";
export function AppShell({ children }: { children: React.ReactNode }) {
  const { workspaceId } = useWorkspace();
  const [pendingApprovals, setPendingApprovals] = useState<number | null>(null);
  useEffect(() => {
    setPendingApprovals(null);
    if (!workspaceId) return;
    let cancelled = false;
    const refresh = async () => {
      try {
        const { data: { session } } = await createClient().auth.getSession();
        if (!session || cancelled) return;
        const response = await api.listApprovals(workspaceId, session.access_token);
        if (!cancelled) setPendingApprovals(response.approvals.length);
      } catch { return; }
    };
    void refresh();
    const timer = window.setInterval(refresh, 30_000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [workspaceId]);
  return <SidebarProvider className="h-svh">
    <AppSidebar pendingApprovals={pendingApprovals ?? 0} />
    <SidebarInset className="min-h-0">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-3 lg:hidden">
        <Link href="/dashboard" className="font-bold">AstaLink</Link>
        <WorkspaceSwitcher variant="header" />
      </header>
      <div className="min-h-0 flex-1 overflow-auto pb-[calc(8rem+env(safe-area-inset-bottom))] lg:pb-0">{children}</div>
    </SidebarInset>
    <MobileNavigation pendingApprovals={pendingApprovals ?? 0} />
  </SidebarProvider>;
}
```

Refactor `WorkspaceSwitcher` to accept `variant: "sidebar" | "header"` while retaining one `handleCreate`, selection state, and API flow. The header variant shows the selected workspace name and opens a `Sheet`; it does not introduce automatic workspace creation.

- [ ] **Step 6: Raise the compact-navigation breakpoint to 1024 and wire the layout**

```typescript
// frontend/hooks/use-mobile.ts
const MOBILE_BREAKPOINT = 1024;
```

In `frontend/components/ui/sidebar.tsx`, change every responsive `md:` variant to its equivalent `lg:` variant so the CSS visibility rules match `useIsMobile`. This includes the desktop sidebar root, fixed panel, inset styling, and hover-action visibility variants. Do not alter non-responsive classes or any color token.

```tsx
// frontend/app/(protected)/layout.tsx
export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return <TooltipProvider><WorkspaceProvider><AppShell>{children}</AppShell></WorkspaceProvider></TooltipProvider>;
}
```

- [ ] **Step 7: Run shell tests, type-check, lint, and commit**

Run: `npm test -- lib/journey-navigation.test.ts components/mobile-navigation.test.tsx`

Run: `npx tsc --noEmit`

Run: `npm run lint -- components/app-shell.tsx components/app-sidebar.tsx components/mobile-navigation.tsx components/workspace-switcher.tsx components/ui/sidebar.tsx app/\(protected\)/layout.tsx hooks/use-mobile.ts`

Expected: all PASS.

```bash
git add frontend/components/app-shell.tsx frontend/components/app-sidebar.tsx frontend/components/mobile-navigation.tsx frontend/components/mobile-navigation.test.tsx frontend/components/workspace-switcher.tsx frontend/components/ui/sidebar.tsx frontend/app/\(protected\)/layout.tsx frontend/hooks/use-mobile.ts
git commit -m "feat(navigation): add journey app shell"
```

### Task 8: Build the Guided Home Against the Projection API

**Files:**
- Modify: `frontend/lib/api-client.ts`
- Create: `frontend/components/home/home-page.tsx`
- Create: `frontend/components/home/financial-snapshot.tsx`
- Create: `frontend/components/home/next-action-card.tsx`
- Create: `frontend/components/home/readiness-card.tsx`
- Create: `frontend/components/home/allocation-preview.tsx`
- Create: `frontend/components/home/activity-list.tsx`
- Create: `frontend/components/home/pending-approvals-card.tsx`
- Create: `frontend/components/home/quick-actions.tsx`
- Create: `frontend/components/home/section-state.tsx`
- Create: `frontend/components/home/home-page.test.tsx`
- Modify: `frontend/app/(protected)/dashboard/page.tsx`

**Interfaces:**
- Consumes: Task 4 endpoint; Task 7 workspace context and shell.
- Produces: frontend `JourneyHomeResponse`, `api.getJourneyHome`, and the final guided `/dashboard`.

- [ ] **Step 1: Add exact client DTOs and method**

```typescript
// frontend/lib/api-client.ts
export type JourneySectionState = "ready" | "empty" | "stale" | "error";
export interface JourneyFinancialMetric {
  key: "cash_balance" | "business_revenue" | "portfolio_value";
  label: string;
  value: number | null;
  unit: "IDR";
  state: JourneySectionState;
  as_of: string | null;
  source: "workspace" | "business_financial_records" | "portfolio";
  change_text: string | null;
}
export interface JourneyHomeResponse {
  workspace_id: string;
  workspace_name: string;
  workspace_type: "personal" | "business";
  generated_at: string;
  financial_snapshot: JourneyFinancialMetric[];
  readiness_summary: { status: "ready" | "needs_input" | "not_ready" | "unavailable"; decisive_gaps: string[]; blocker_codes: string[]; continuation_href: string };
  next_action: { kind: string; title: string; rationale: string; href: string; rule_id: string };
  allocation_preview: { cash: number; stocks: number; business: number; confidence_label: "terbatas" | "cukup" | "kuat"; as_of: string; data_gaps: string[] } | null;
  recent_activity: { id: string; kind: string; title: string; amount: number | null; status: string; occurred_at: string; href: string }[];
  pending_approvals_count: number;
  section_health: Record<string, { state: JourneySectionState; message: string | null }>;
}

getJourneyHome: (workspaceId: string, token: string): Promise<JourneyHomeResponse> =>
  jsonFetch(`/api/v1/journey/home?workspace_id=${encodeURIComponent(workspaceId)}`, { method: "GET" }, token),
```

- [ ] **Step 2: Write failing home-state tests**

```typescript
// frontend/components/home/home-page.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { HomePage } from "./home-page";
import { api } from "@/lib/api-client";

vi.mock("@/components/workspace-context", () => ({ useWorkspace: vi.fn() }));
vi.mock("@/lib/supabase/client", () => ({ createClient: () => ({ auth: { getSession: async () => ({ data: { session: { access_token: "x" } } }) } }) }));

test("does not request home without a workspace", async () => {
  const { useWorkspace } = await import("@/components/workspace-context");
  vi.mocked(useWorkspace).mockReturnValue({ workspaceId: null } as never);
  const spy = vi.spyOn(api, "getJourneyHome");
  render(<HomePage />);
  expect(screen.getByText(/pilih workspace/i)).toBeInTheDocument();
  expect(spy).not.toHaveBeenCalled();
});

test("renders a failed section without turning it into zero", async () => {
  const { useWorkspace } = await import("@/components/workspace-context");
  vi.mocked(useWorkspace).mockReturnValue({ workspaceId: "ws-1" } as never);
  vi.spyOn(api, "getJourneyHome").mockResolvedValue({
    workspace_id: "ws-1", workspace_name: "Personal", workspace_type: "personal",
    generated_at: "2026-09-20T03:30:00Z",
    financial_snapshot: [{ key: "portfolio_value", label: "Portofolio sandbox",
      value: null, unit: "IDR", state: "error", as_of: null, source: "portfolio", change_text: null }],
    readiness_summary: { status: "unavailable", decisive_gaps: [], blocker_codes: [], continuation_href: "/allocation" },
    next_action: { kind: "ask_asta", title: "Mulai", rationale: "Mulai", href: "/chatbot", rule_id: "fallback" },
    allocation_preview: null, recent_activity: [], pending_approvals_count: 0,
    section_health: { portfolio: { state: "error", message: "Bagian ini belum dapat diperbarui." } },
  });
  render(<HomePage />);
  await waitFor(() => expect(screen.getByText(/belum dapat diperbarui/i)).toBeInTheDocument());
  expect(screen.queryByText("Rp 0")).not.toBeInTheDocument();
});
```

- [ ] **Step 3: Run tests and confirm `HomePage` is missing**

Run: `npm test -- components/home/home-page.test.tsx`

Expected: FAIL because the home components do not exist.

- [ ] **Step 4: Implement the home state machine and focused components**

```tsx
// frontend/components/home/home-page.tsx
"use client";
export function HomePage() {
  const { workspaceId } = useWorkspace();
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [data, setData] = useState<JourneyHomeResponse | null>(null);
  useEffect(() => {
    if (!workspaceId) { setState("idle"); setData(null); return; }
    let cancelled = false;
    setState("loading");
    (async () => {
      try {
        const { data: { session } } = await createClient().auth.getSession();
        if (!session) throw new Error("Missing authenticated session");
        const result = await api.getJourneyHome(workspaceId, session.access_token);
        if (!cancelled) { setData(result); setState("ready"); }
      } catch { if (!cancelled) setState("error"); }
    })();
    return () => { cancelled = true; };
  }, [workspaceId]);
  if (!workspaceId) return <WorkspaceRequired />;
  if (state === "loading" || state === "idle") return <HomeSkeleton />;
  if (state === "error" || !data) return <HomeLoadError />;
  return <JourneyHomeContent data={data} />;
}
```

Use the current theme classes only. Layout contract:

```tsx
<main className="mx-auto min-h-full w-full max-w-7xl space-y-4 p-4 sm:p-6 lg:p-8">
  <PageHeader
    eyebrow={data.workspace_name}
    title="Selamat datang kembali"
    description={`Terakhir diperbarui ${formatJourneyTime(data.generated_at)}`}
  />
  <FinancialSnapshot metrics={data.financial_snapshot} />
  <NextActionCard action={data.next_action} />
  <div className="grid gap-4 lg:grid-cols-2">
    <ReadinessCard summary={data.readiness_summary} />
    <AllocationPreview preview={data.allocation_preview} />
  </div>
  <div className="grid gap-4 lg:grid-cols-2">
    <ActivityList items={data.recent_activity} />
    <div className="space-y-4">
      <PendingApprovalsCard count={data.pending_approvals_count} href="/approvals" />
      <QuickActions />
    </div>
  </div>
</main>
```

`QuickActions` contains three visually secondary links: `Catat transaksi` to `/transactions`, `Rencana dana` to `/allocation`, and `Tanya Asta` to `/chatbot`. `SectionState` renders `empty`, `stale`, and `error` distinctly; stale content keeps its value and timestamp, error content uses `section_health.message`, and only an error state gets a `Coba lagi` control that reruns the home request.

- [ ] **Step 5: Replace the temporary dashboard terminal wrapper**

```tsx
// frontend/app/(protected)/dashboard/page.tsx
import { HomePage } from "@/components/home/home-page";
export default function DashboardPage() { return <HomePage />; }
```

- [ ] **Step 6: Run home tests and static checks, then commit**

Run: `npm test -- components/home/home-page.test.tsx`

Run: `npx tsc --noEmit`

Run: `npm run lint -- components/home app/\(protected\)/dashboard/page.tsx lib/api-client.ts`

Expected: all PASS.

```bash
git add frontend/lib/api-client.ts frontend/components/home frontend/app/\(protected\)/dashboard/page.tsx
git commit -m "feat(home): add guided journey dashboard"
```

### Task 9: Convert Transaction and Portfolio Data for Mobile and Add Accessible Responsive Dialogs

**Files:**
- Create: `frontend/components/transactions/transaction-view.tsx`
- Create: `frontend/components/transactions/transaction-view.test.tsx`
- Modify: `frontend/app/(protected)/transactions/page.tsx`
- Create: `frontend/components/portfolio/holdings-view.tsx`
- Create: `frontend/components/portfolio/holdings-view.test.tsx`
- Modify: `frontend/app/(protected)/portfolio/page.tsx`
- Create: `frontend/components/ui/responsive-dialog.tsx`
- Modify: `frontend/components/allocation-buy-modal.tsx`

**Interfaces:**
- Consumes: current transaction and portfolio models; `useIsMobile` compact breakpoint.
- Produces: responsive table/card views and `ResponsiveDialog` using Base UI focus management.

- [ ] **Step 1: Write failing tests proving the same data appears in desktop and mobile representations**

```tsx
// frontend/components/transactions/transaction-view.test.tsx
import { render, screen } from "@testing-library/react";
import { TransactionView } from "./transaction-view";

test("renders transaction semantics in table and card views", () => {
  render(<TransactionView items={[{ id: "t1", ticker: "BBCA", side: "buy",
    quantity: 100, price: 9000, status: "filled", broker_ref: null,
    created_at: "2026-09-20T03:30:00Z" }]} />);
  expect(screen.getAllByText("BBCA")).toHaveLength(2);
  expect(screen.getAllByText(/Rp 900.000/)).toHaveLength(2);
});
```

```tsx
// frontend/components/portfolio/holdings-view.test.tsx
import { render, screen } from "@testing-library/react";
import { HoldingsView } from "./holdings-view";

test("keeps unavailable prices explicit in both layouts", () => {
  render(<HoldingsView holdings={[{ ticker: "BBCA", quantity: 100, avg_cost: 9000,
    cost_basis: 900000, last_price: null, market_value: null,
    unrealized_pnl: null, unrealized_pnl_pct: null }]} onBuy={() => {}} onSell={() => {}} totalEquity={null} />);
  expect(screen.getAllByText("—").length).toBeGreaterThan(1);
  expect(screen.queryByText("Rp 0")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests and confirm the view components are missing**

Run: `npm test -- components/transactions/transaction-view.test.tsx components/portfolio/holdings-view.test.tsx`

Expected: FAIL because both components are missing.

- [ ] **Step 3: Extract responsive table/card views**

Create `TransactionView` and `HoldingsView` from the current table bodies. Each component must render two representations of the same input data:

- below `lg`, a `space-y-3` list of bordered `article` cards;
- at `lg` and above, the current semantic `table` inside its existing bounded `overflow-x-auto` container;
- transaction cards show description/ticker first, signed nominal second, then side/status and localized date;
- holding cards show ticker first, quantity and average cost second, then market value and unrealized P&L;
- every nullable price, value, and P&L uses the same em dash formatter as the desktop table—never coerce `null` to zero;
- buy and sell buttons call the same callbacks with the same ticker used by the desktop row.

Use `p-4 sm:p-6 lg:p-8` on page wrappers. Keep cards and tables in the DOM for CSS-only responsive switching; mark the hidden representation with CSS `display:none`, which removes it from the accessibility tree.

- [ ] **Step 4: Add a focus-managed responsive dialog primitive**

```tsx
// frontend/components/ui/responsive-dialog.tsx
"use client";
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";

export function ResponsiveDialog({ open, onOpenChange, title, description, children }:
  { open: boolean; onOpenChange: (open: boolean) => void; title: string; description?: string; children: React.ReactNode }) {
  return <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
    <DialogPrimitive.Portal>
      <DialogPrimitive.Backdrop className="fixed inset-0 z-50 bg-background/80 backdrop-blur-md" />
      <DialogPrimitive.Popup className="fixed inset-x-0 bottom-0 z-50 max-h-[90svh] overflow-y-auto rounded-t-2xl border border-border bg-card p-5 shadow-xl lg:left-1/2 lg:top-1/2 lg:bottom-auto lg:max-w-md lg:-translate-x-1/2 lg:-translate-y-1/2 lg:rounded-2xl">
        <DialogPrimitive.Title className="text-lg font-bold">{title}</DialogPrimitive.Title>
        {description && <DialogPrimitive.Description className="mt-1 text-xs text-muted-foreground">{description}</DialogPrimitive.Description>}
        {children}
      </DialogPrimitive.Popup>
    </DialogPrimitive.Portal>
  </DialogPrimitive.Root>;
}
```

Replace the handmade fixed overlays in `SellModal` and `AllocationBuyModal` with `ResponsiveDialog`; retain validation, PIN behavior, callbacks, and theme classes.

- [ ] **Step 5: Run tests, type-check, lint, and commit**

Run: `npm test -- components/transactions/transaction-view.test.tsx components/portfolio/holdings-view.test.tsx`

Run: `npx tsc --noEmit`

Run: `npm run lint -- components/transactions components/portfolio components/ui/responsive-dialog.tsx components/allocation-buy-modal.tsx app/\(protected\)/transactions/page.tsx app/\(protected\)/portfolio/page.tsx`

Expected: all PASS.

```bash
git add frontend/components/transactions frontend/components/portfolio frontend/components/ui/responsive-dialog.tsx frontend/components/allocation-buy-modal.tsx frontend/app/\(protected\)/transactions/page.tsx frontend/app/\(protected\)/portfolio/page.tsx
git commit -m "feat(responsive): adapt transactions and portfolio"
```

### Task 10: Make the Market Terminal and Remaining Journey Pages Responsive

**Files:**
- Modify: `frontend/components/terminal/market-terminal.tsx`
- Modify: `frontend/components/terminal/watchlist-sidebar.tsx`
- Modify: `frontend/components/terminal/chart-toolbar.tsx`
- Create: `frontend/components/terminal/mobile-watchlist-sheet.tsx`
- Modify: `frontend/app/(protected)/allocation/page.tsx`
- Modify: `frontend/app/(protected)/recommendations/page.tsx`
- Modify: `frontend/app/(protected)/news/page.tsx`
- Modify: `frontend/app/(protected)/business/page.tsx`
- Modify: `frontend/app/(protected)/approvals/page.tsx`
- Modify: `frontend/app/(protected)/settings/page.tsx`
- Modify: `frontend/app/(protected)/chatbot/page.tsx`
- Create: `frontend/components/terminal/market-terminal-responsive.test.tsx`

**Interfaces:**
- Consumes: Task 7 compact breakpoint and Task 9 dialog/card patterns.
- Produces: mobile-first page layouts without changing theme colors, market data behavior, or domain actions.

- [ ] **Step 1: Write a failing terminal responsive-contract test**

```tsx
// frontend/components/terminal/market-terminal-responsive.test.tsx
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { MarketTerminal } from "./market-terminal";

vi.mock("@/components/workspace-context", () => ({ useWorkspace: () => ({ workspaceId: null }) }));

test("offers a labeled mobile watchlist control and keeps the chart landmark", () => {
  render(<MarketTerminal />);
  expect(screen.getByRole("button", { name: /buka daftar saham/i })).toBeInTheDocument();
  expect(screen.getByRole("main", { name: /grafik pasar/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test and verify the mobile control is missing**

Run: `npm test -- components/terminal/market-terminal-responsive.test.tsx`

Expected: FAIL because no mobile watchlist control exists.

- [ ] **Step 3: Transform the terminal at the agreed breakpoints**

Wrap the existing `WatchlistSidebar` call in `className="hidden lg:block"`, keeping its six current props unchanged. Add `MobileWatchlistSheet` immediately inside the chart column and pass it those same six values: `watchlist`, `selectedTicker`, `onSelect={setSelectedTicker}`, `collapsed`, `onToggle={() => setCollapsed(!collapsed)}`, and `loading={marketLoading}`. Render its trigger only below `lg` with accessible name `Buka daftar saham`.

Add `aria-label="Grafik pasar"` to the existing chart `<main>`, preserve every current `ChartToolbar` and `MainChartArea` prop exactly, change only the chart-content padding from `p-4` to `p-3 sm:p-4`, and keep `BusinessConditionPanel` after the terminal row.

`MobileWatchlistSheet` uses existing `Sheet` with `side="bottom"`. `ChartToolbar` uses horizontally scrollable controls within its own bounded region, never page-level overflow. Do not add polling or data-source changes in this task.

- [ ] **Step 4: Apply exact responsive/copy changes to the remaining pages**

Use these replacements:

```text
All page wrappers:
  p-8 -> p-4 sm:p-6 lg:p-8

allocation/page.tsx:
  eyebrow "Layer 0 — Gerbang Kelayakan" -> "Rencana Dana"
  title "Alokasi Modal" -> "Rencana Dana"
  "Layer 1 — Stock Engine" -> "Pilihan investasi"
  internal confidence label -> user-facing terbatas/cukup/kuat
  keep md:grid-cols-2 only where cards remain readable at 768 px

recommendations/page.tsx:
  eyebrow "AI Rekomendasi" -> "Eksplorasi"
  title "Saham Layak Dibeli" -> "Ide Investasi"
  candidate table -> lg table plus mobile cards, same data values

news, business, approvals, settings:
  responsive wrapper padding; buttons use min-h-11; card rows wrap rather than overflow

chatbot/page.tsx:
  conversation aside breakpoint md -> lg
  message container px-6 -> px-3 sm:px-6
  user max width 75% -> max-w-[90%] sm:max-w-[75%]
  assistant max width 85% -> max-w-[95%] sm:max-w-[85%]
  composer controls keep 44 px targets and leave shell bottom padding unobstructed
```

- [ ] **Step 5: Run focused tests and static checks**

Run: `npm test -- components/terminal/market-terminal-responsive.test.tsx components/home/home-page.test.tsx components/mobile-navigation.test.tsx`

Run: `npx tsc --noEmit`

Run: `npm run lint`

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/terminal frontend/app/\(protected\)/allocation/page.tsx frontend/app/\(protected\)/recommendations/page.tsx frontend/app/\(protected\)/news/page.tsx frontend/app/\(protected\)/business/page.tsx frontend/app/\(protected\)/approvals/page.tsx frontend/app/\(protected\)/settings/page.tsx frontend/app/\(protected\)/chatbot/page.tsx
git commit -m "feat(responsive): adapt journey destinations"
```

### Task 11: Remove Obsolete Routes and Update Product Documentation

**Files:**
- Delete if no consumer remains: `frontend/app/(protected)/business/detail/page.tsx`
- Modify: any links found by the required repository search
- Modify: `README.md`
- Modify: `docs/astalink-vision-positioning.md`

**Interfaces:**
- Consumes: final routes and labels from Tasks 5–10.
- Produces: no compatibility route without a consumer, no obsolete navigation label, and current product documentation.

- [ ] **Step 1: Prove whether the legacy business shortcut has consumers**

Run:

```bash
rg -n 'business/detail|Dasbor|Chatbot AI|Saham Layak Dibeli|Layer 0|Layer 1' frontend README.md docs/astalink-vision-positioning.md
```

Expected: `/business/detail` appears only in the legacy shortcut or stale links; old user-facing labels appear only in files scheduled for update. If a real external compatibility requirement is documented, retain a redirect-only route with a removal comment naming that requirement; otherwise delete the route.

- [ ] **Step 2: Delete or replace every stale consumer**

```tsx
// Canonical business-detail links always use the ID route:
<Link href={`/business/${business.id}`}>Buka bisnis</Link>
```

Delete `frontend/app/(protected)/business/detail/page.tsx` after all consumers use `/business/[businessId]`. Do not leave its implementation commented out.

- [ ] **Step 3: Update route and experience documentation**

Update README capability/route language to state:

```markdown
- Beranda merangkum kondisi, kesiapan, aktivitas terbaru, dan satu langkah berikutnya.
- Pasar & Grafik tersedia di `/market`; `/dashboard` adalah Beranda terpandu.
- Navigasi mengikuti Catat & Kelola, Rencanakan, Eksplorasi, dan Portofolio.
```

Update `docs/astalink-vision-positioning.md` only where route or navigation semantics changed. Do not alter its financial-coach positioning or theme direction.

- [ ] **Step 4: Run dead-code and route checks**

Run:

```bash
rg -n 'business/detail|NAV_SECTIONS|function MiniStat|Hidden per concept change|Astalink Console' frontend
```

Expected: no matches.

Run: `npx tsc --noEmit`

Run: `npm run lint`

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend README.md docs/astalink-vision-positioning.md
git commit -m "docs: align product routes with journey navigation"
```

### Task 12: Run Full Verification and Enforce Cleanup/Theme Gates

**Files:**
- Modify only files required to fix failures found by this task.

**Interfaces:**
- Consumes: all earlier tasks.
- Produces: verified workstream with no known regression, stale code, or theme-color change.

- [ ] **Step 1: Run the complete backend suite**

Run: `docker compose exec backend pytest -q`

Expected: PASS with zero failures.

- [ ] **Step 2: Run all frontend automated checks**

Run from `frontend/`:

```bash
npm test
npx tsc --noEmit
npm run lint
npm run build
```

Expected: every command exits 0.

- [ ] **Step 3: Verify routes and the five end-to-end journeys manually**

Run the development stack, authenticate with a test account, and check:

```text
1. /dashboard shows guided home; /market shows the terminal.
2. Confirm a business transaction; home activity and supported omset update after reload.
3. Follow a readiness gap to /allocation/investor and return to /dashboard.
4. Navigate /recommendations -> /market -> /portfolio with correct active families.
5. Resolve /approvals/:id; approval badge and next action update.
```

Expected: all journeys complete without a broken route or repeated data entry.

- [ ] **Step 4: Verify responsive and accessibility behavior**

At viewport widths `360`, `768`, `1024`, and `1440`, check:

```text
- no page-level horizontal scroll on primary routes;
- bottom navigation and Tanya Asta do not cover content or primary buttons;
- mobile tables render as cards;
- market watchlist opens as a sheet below 1024;
- dialogs trap focus, close with Escape, restore focus, and keep the main button above the keyboard area;
- every icon-only button has an accessible name;
- keyboard focus is visible;
- reduced-motion preference removes nonessential entry animation.
```

Expected: all checks pass. Record any failure as a reproducible issue and fix it before proceeding.

- [ ] **Step 5: Enforce the no-theme-change gate**

Run from repository root, using the approved-spec commit as the baseline:

```bash
git diff df683b9 -- frontend/app/globals.css
git diff df683b9 -- frontend | rg '^\+.*(#[0-9A-Fa-f]{3,8}|oklch\()'
```

Expected: neither command prints output. The first prevents token or theme-mode edits; the second prevents new literal colors elsewhere in the frontend. If output appears, revert only the theme/color changes introduced by this workstream; do not discard unrelated user changes.

- [ ] **Step 6: Enforce the cleanup gate**

Run:

```bash
rg -n 'TO[D]O|FIXM[E]|commented.?out|business/detail|NAV_SECTIONS|Astalink Console|Hidden per concept change' frontend backend/app
git status --short
git diff --check
```

Expected: no newly introduced unfinished markers, no obsolete journey code, no unexpected files, and no whitespace errors. Existing unrelated unfinished markers must be documented rather than edited outside scope. If verification requires a code change, return to the owning task, apply the correction there, repeat that task's focused checks and commit, then rerun all of Task 12. Do not create a generic verification commit or an empty commit.
