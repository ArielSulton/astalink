from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.journey_home import SupabaseJourneySource, build_journey_home
from app.models.portfolio import PortfolioResponse


NOW = datetime(2026, 9, 20, 3, 30, tzinfo=UTC)


def _source() -> MagicMock:
    source = MagicMock()
    source.load_workspace.return_value = {
        "id": "ws-1",
        "name": "Personal",
        "type": "personal",
        "cash_balance": 10_000_000,
    }
    source.load_business_summary.return_value = {"value": 2_000_000, "as_of": NOW}
    source.load_portfolio.return_value = PortfolioResponse(
        workspace_id="ws-1",
        cash_balance=10_000_000,
        holdings=[],
    )
    source.load_readiness.return_value = {
        "status": "needs_input",
        "gaps": ["monthly_expenses"],
        "blockers": [],
    }
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
        workspace_id="ws-1",
        cash_balance=10_000_000,
        holdings=[],
        total_market_value=None,
        total_equity=None,
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


def test_home_omits_business_metric_when_workspace_has_no_business_data() -> None:
    source = _source()
    source.load_business_summary.return_value = None
    result = build_journey_home(source, now=NOW)
    assert all(metric.key != "business_revenue" for metric in result.financial_snapshot)
    assert result.section_health["business"].state == "empty"


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = [dict(row) for row in rows]

    def select(self, _columns: str) -> "_Query":
        return self

    def eq(self, field: str, value: object) -> "_Query":
        self.rows = [row for row in self.rows if row.get(field) == value]
        return self

    def in_(self, field: str, values: list[str]) -> "_Query":
        self.rows = [row for row in self.rows if row.get(field) in values]
        return self

    def order(self, field: str, desc: bool = False) -> "_Query":
        self.rows.sort(key=lambda row: row.get(field) or "", reverse=desc)
        return self

    def limit(self, count: int) -> "_Query":
        self.rows = self.rows[:count]
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self.rows)


class _Supabase:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        return _Query(self.tables.get(name, []))


def test_supabase_source_normalizes_domain_data_and_acknowledgement() -> None:
    tables = {
        "workspaces": [{"id": "ws-1", "name": "Toko", "type": "business", "cash_balance": 10_000_000}],
        "businesses": [{"id": "biz-1", "workspace_id": "ws-1"}],
        "business_financial_records": [{
            "business_id": "biz-1", "omset": 2_000_000, "period_year": 2026,
            "created_at": "2026-09-19T03:30:00+00:00",
        }],
        "business_transactions": [
            {"id": "btx-1", "business_id": "biz-1", "status": "confirmed", "type": "income",
             "item_description": "Penjualan harian", "amount": 250_000,
             "occurred_at": "2026-09-19T04:00:00+00:00", "confirmed_at": "2026-09-19T04:05:00+00:00"},
            {"id": "btx-2", "business_id": "biz-1", "status": "pending_confirmation",
             "created_at": "2026-09-20T02:00:00+00:00"},
        ],
        "investor_profiles": [{"workspace_id": "ws-1", "profile": {
            "monthly_expenses": 2_000_000, "emergency_fund": 20_000_000,
            "capital_is_borrowed": False, "horizon_months": 36,
        }}],
        "chat_conversations": [{"id": "conv-1", "workspace_id": "ws-1", "user_id": "user-1",
                                "updated_at": "2026-09-19T05:00:00+00:00"}],
        "chat_messages": [{
            "conversation_id": "conv-1", "role": "assistant", "audit_id": "audit-ack",
            "created_at": "2026-09-19T05:00:00+00:00",
            "metadata": {"layer0_result": {
                "allocation": {"cash": 0.2, "stocks": 0.5, "business": 0.3},
                "confidence_label": "HIGH", "questions": [],
            }},
        }],
        "transactions": [{
            "id": "trade-1", "workspace_id": "ws-1", "ticker": "BBCA", "side": "buy",
            "quantity": 10, "price": 10_000, "status": "filled",
            "executed_at": "2026-09-18T03:00:00+00:00", "created_at": "2026-09-18T03:00:00+00:00",
        }],
        "audit_log": [
            {"audit_id": "audit-ack", "workspace_id": "ws-1", "user_id": "user-1",
             "status": "acknowledged", "created_at": "2026-09-19T05:00:00+00:00"},
            {"audit_id": "audit-pending", "workspace_id": "ws-1", "user_id": "user-1",
             "status": "awaiting_approval", "intent": "allocate",
             "created_at": "2026-09-20T01:00:00+00:00"},
        ],
    }
    source = SupabaseJourneySource(_Supabase(tables), "ws-1", "user-1", today=lambda: NOW)

    with patch("app.core.journey_home.build_portfolio", return_value=PortfolioResponse(
        workspace_id="ws-1", cash_balance=10_000_000, holdings=[],
    )):
        assert source.load_workspace()["name"] == "Toko"
        assert source.load_portfolio().cash_balance == 10_000_000

    assert source.load_business_summary()["value"] == 2_000_000
    assert source.load_readiness()["status"] == "ready"
    assert source.load_pending() == {"transaction_id": "btx-2", "approvals": 1}
    allocation = source.load_allocation_preview()
    assert allocation.preview.confidence_label == "kuat"
    assert allocation.acknowledged is True
    activity = source.load_recent_activity()
    assert [item.kind for item in activity] == ["approval", "business_transaction", "sandbox_trade"]
