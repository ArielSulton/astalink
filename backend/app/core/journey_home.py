from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from app.agents.allocation.constraints import evaluate_constraints
from app.agents.allocation.schemas import InvestorProfile
from app.core.journey_next_action import JourneySignals, choose_next_action
from app.core.portfolio_read import build_portfolio
from app.models.journey import (
    ActivityItem,
    AllocationPreview,
    FinancialMetric,
    JourneyHomeResponse,
    ReadinessSummary,
    SectionHealth,
    SectionState,
)

log = logging.getLogger(__name__)

BUSINESS_STALE_AFTER = timedelta(days=31)
ALLOCATION_STALE_AFTER = timedelta(days=7)
ACKNOWLEDGED_AUDIT_STATUSES = {"acknowledged", "approved", "executed"}


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("timestamp is missing")
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


@dataclass(frozen=True)
class AllocationSource:
    preview: AllocationPreview
    acknowledged: bool


class SupabaseJourneySource:
    def __init__(
        self,
        sb,
        workspace_id: str,
        user_id: str,
        today: Callable[[], datetime] | None = None,
    ) -> None:
        self.sb = sb
        self.workspace_id = workspace_id
        self.user_id = user_id
        self._today = today or (lambda: datetime.now(UTC))

    def _business_ids(self) -> list[str]:
        rows = (
            self.sb.table("businesses").select("id")
            .eq("workspace_id", self.workspace_id).execute().data
        ) or []
        return [str(row["id"]) for row in rows]

    def load_workspace(self) -> dict:
        rows = (
            self.sb.table("workspaces").select("id,name,type,cash_balance")
            .eq("id", self.workspace_id).limit(1).execute().data
        ) or []
        if not rows:
            raise LookupError("workspace missing after ownership check")
        return rows[0]

    def load_portfolio(self):
        return build_portfolio(self.sb, self.workspace_id)

    def load_business_summary(self) -> dict | None:
        business_ids = self._business_ids()
        if not business_ids:
            return None
        records = (
            self.sb.table("business_financial_records")
            .select("omset,period_year,created_at")
            .in_("business_id", business_ids)
            .eq("period_year", self._today().year)
            .execute().data
        ) or []
        if not records:
            return None
        confirmations = (
            self.sb.table("business_transactions").select("confirmed_at")
            .in_("business_id", business_ids).eq("status", "confirmed")
            .order("confirmed_at", desc=True).limit(1).execute().data
        ) or []
        timestamps = [row.get("created_at") for row in records if row.get("created_at")]
        if confirmations and confirmations[0].get("confirmed_at"):
            timestamps.append(confirmations[0]["confirmed_at"])
        return {
            "value": sum(float(row["omset"]) for row in records),
            "as_of": max(_as_datetime(value) for value in timestamps),
        }

    def load_readiness(self) -> dict:
        rows = (
            self.sb.table("investor_profiles").select("profile")
            .eq("workspace_id", self.workspace_id).limit(1).execute().data
        ) or []
        investor = InvestorProfile.model_validate((rows[0] if rows else {}).get("profile") or {})
        decisive = (
            "monthly_expenses",
            "emergency_fund",
            "capital_is_borrowed",
            "horizon_months",
        )
        gaps = [name for name in decisive if getattr(investor, name) is None]
        constraints = evaluate_constraints(investor)
        blockers = [flag.code for flag in constraints.veto_flags if flag.hard]
        status = "needs_input" if gaps else "not_ready" if blockers else "ready"
        return {"status": status, "gaps": gaps, "blockers": blockers}

    def load_pending(self) -> dict:
        business_ids = self._business_ids()
        pending_transactions: list[dict] = []
        if business_ids:
            pending_transactions = (
                self.sb.table("business_transactions").select("id,created_at")
                .in_("business_id", business_ids)
                .eq("status", "pending_confirmation")
                .order("created_at", desc=True).limit(1).execute().data
            ) or []
        approvals = (
            self.sb.table("audit_log").select("audit_id")
            .eq("workspace_id", self.workspace_id).eq("user_id", self.user_id)
            .eq("status", "awaiting_approval").execute().data
        ) or []
        return {
            "transaction_id": pending_transactions[0]["id"] if pending_transactions else None,
            "approvals": len(approvals),
        }

    def load_allocation_preview(self) -> AllocationSource | None:
        conversations = (
            self.sb.table("chat_conversations").select("id")
            .eq("workspace_id", self.workspace_id).eq("user_id", self.user_id)
            .order("updated_at", desc=True).execute().data
        ) or []
        conversation_ids = [str(row["id"]) for row in conversations]
        if not conversation_ids:
            return None
        messages = (
            self.sb.table("chat_messages").select("metadata,created_at,audit_id")
            .in_("conversation_id", conversation_ids).eq("role", "assistant")
            .order("created_at", desc=True).limit(20).execute().data
        ) or []
        confidence_labels = {"LOW": "terbatas", "MEDIUM": "cukup", "HIGH": "kuat"}
        for message in messages:
            layer0 = (message.get("metadata") or {}).get("layer0_result") or {}
            allocation = layer0.get("allocation")
            if not allocation:
                continue
            questions = layer0.get("questions") or []
            gaps = [
                str(item.get("field") if isinstance(item, dict) else item)
                for item in questions
            ]
            confidence = confidence_labels.get(str(layer0.get("confidence_label", "LOW")).upper(), "terbatas")
            preview = AllocationPreview(
                cash=float(allocation["cash"]),
                stocks=float(allocation["stocks"]),
                business=float(allocation["business"]),
                confidence_label=confidence,
                as_of=_as_datetime(message["created_at"]),
                data_gaps=gaps,
            )
            audit_id = message.get("audit_id")
            acknowledged = False
            if audit_id:
                audits = (
                    self.sb.table("audit_log").select("status")
                    .eq("audit_id", audit_id).eq("workspace_id", self.workspace_id)
                    .eq("user_id", self.user_id).limit(1).execute().data
                ) or []
                acknowledged = bool(
                    audits and audits[0].get("status") in ACKNOWLEDGED_AUDIT_STATUSES
                )
            return AllocationSource(preview=preview, acknowledged=acknowledged)
        return None

    def load_recent_activity(self) -> list[ActivityItem]:
        activities: list[ActivityItem] = []
        business_ids = self._business_ids()
        if business_ids:
            rows = (
                self.sb.table("business_transactions")
                .select("id,business_id,item_description,type,amount,status,occurred_at,confirmed_at")
                .in_("business_id", business_ids).eq("status", "confirmed")
                .order("confirmed_at", desc=True).limit(6).execute().data
            ) or []
            for row in rows:
                direction = "Pemasukan" if row.get("type") == "income" else "Pengeluaran"
                activities.append(ActivityItem(
                    id=str(row["id"]),
                    kind="business_transaction",
                    title=f"{direction}: {row.get('item_description') or 'Transaksi bisnis'}",
                    amount=float(row["amount"]) if row.get("amount") is not None else None,
                    status=str(row.get("status") or "confirmed"),
                    occurred_at=_as_datetime(row.get("confirmed_at") or row.get("occurred_at")),
                    href=f"/business/{row['business_id']}",
                ))

        trades = (
            self.sb.table("transactions")
            .select("id,ticker,side,quantity,price,status,executed_at,created_at")
            .eq("workspace_id", self.workspace_id)
            .order("executed_at", desc=True).limit(6).execute().data
        ) or []
        for row in trades:
            quantity = float(row["quantity"]) if row.get("quantity") is not None else None
            price = float(row["price"]) if row.get("price") is not None else None
            amount = quantity * price if quantity is not None and price is not None else None
            side = "Beli" if row.get("side") == "buy" else "Jual"
            activities.append(ActivityItem(
                id=str(row["id"]),
                kind="sandbox_trade",
                title=f"{side} {row.get('ticker') or 'saham'}",
                amount=amount,
                status=str(row.get("status") or "unknown"),
                occurred_at=_as_datetime(row.get("executed_at") or row.get("created_at")),
                href="/portfolio",
            ))

        approvals = (
            self.sb.table("audit_log").select("audit_id,intent,status,created_at")
            .eq("workspace_id", self.workspace_id).eq("user_id", self.user_id)
            .eq("status", "awaiting_approval")
            .order("created_at", desc=True).limit(6).execute().data
        ) or []
        for row in approvals:
            activities.append(ActivityItem(
                id=str(row["audit_id"]),
                kind="approval",
                title=str(row.get("intent") or "Persetujuan menunggu"),
                status="awaiting_approval",
                occurred_at=_as_datetime(row["created_at"]),
                href=f"/approvals/{row['audit_id']}",
            ))

        return sorted(activities, key=lambda item: item.occurred_at, reverse=True)[:6]


def build_journey_home(
    source: SupabaseJourneySource,
    now: datetime | None = None,
) -> JourneyHomeResponse:
    generated_at = now or datetime.now(UTC)
    workspace = source.load_workspace()
    health: dict[str, SectionHealth] = {}

    def capture(name: str, loader, fallback):
        try:
            value = loader()
            health[name] = SectionHealth(state=SectionState.READY)
            return value
        except Exception:
            log.exception("journey_home: %s load failed", name)
            health[name] = SectionHealth(
                state=SectionState.ERROR,
                message="Bagian ini belum dapat diperbarui.",
            )
            return fallback

    business = capture("business", source.load_business_summary, None)
    portfolio = capture("portfolio", source.load_portfolio, None)
    readiness = capture(
        "readiness",
        source.load_readiness,
        {"status": "unavailable", "gaps": [], "blockers": []},
    )
    allocation_source = capture("allocation", source.load_allocation_preview, None)
    activity = capture("activity", source.load_recent_activity, [])
    pending = capture(
        "pending",
        source.load_pending,
        {"transaction_id": None, "approvals": 0},
    )

    business_state = health["business"].state
    if business_state != SectionState.ERROR:
        business_state = (
            SectionState.EMPTY
            if business is None
            else SectionState.STALE
            if generated_at - business["as_of"] > BUSINESS_STALE_AFTER
            else SectionState.READY
        )
        health["business"] = SectionHealth(state=business_state)

    portfolio_state = health["portfolio"].state
    if portfolio_state != SectionState.ERROR:
        portfolio_state = (
            SectionState.EMPTY
            if portfolio is None or portfolio.total_market_value is None
            else SectionState.READY
        )
        health["portfolio"] = SectionHealth(state=portfolio_state)

    allocation = allocation_source.preview if allocation_source else None
    allocation_acknowledged = allocation_source.acknowledged if allocation_source else False
    allocation_state = health["allocation"].state
    if allocation_state != SectionState.ERROR:
        allocation_state = (
            SectionState.EMPTY
            if allocation is None
            else SectionState.STALE
            if generated_at - allocation.as_of > ALLOCATION_STALE_AFTER
            else SectionState.READY
        )
        health["allocation"] = SectionHealth(state=allocation_state)

    if health["activity"].state != SectionState.ERROR and not activity:
        health["activity"] = SectionHealth(state=SectionState.EMPTY)
    if health["pending"].state != SectionState.ERROR and not (
        pending["transaction_id"] or pending["approvals"]
    ):
        health["pending"] = SectionHealth(state=SectionState.EMPTY)

    metrics = [FinancialMetric(
        key="cash_balance",
        label="Kas tersedia",
        value=float(workspace["cash_balance"]),
        state=SectionState.READY,
        as_of=generated_at,
        source="workspace",
    )]
    if business is not None or business_state == SectionState.ERROR:
        metrics.append(FinancialMetric(
            key="business_revenue",
            label="Omset tahun ini",
            value=business["value"] if business else None,
            state=business_state,
            as_of=business["as_of"] if business else None,
            source="business_financial_records",
        ))
    metrics.append(FinancialMetric(
        key="portfolio_value",
        label="Portofolio sandbox",
        value=portfolio.total_market_value if portfolio else None,
        state=portfolio_state,
        as_of=generated_at if portfolio else None,
        source="portfolio",
    ))

    signals = JourneySignals(
        pending_transaction_id=pending["transaction_id"],
        pending_approvals_count=pending["approvals"],
        decisive_gaps=tuple(readiness["gaps"]),
        hard_veto_codes=tuple(readiness["blockers"]),
        allocation_available=allocation is not None,
        allocation_acknowledged=allocation_acknowledged,
        holdings_count=len(portfolio.holdings) if portfolio else 0,
    )
    return JourneyHomeResponse(
        workspace_id=workspace["id"],
        workspace_name=workspace["name"],
        workspace_type=workspace["type"],
        generated_at=generated_at,
        financial_snapshot=metrics,
        readiness_summary=ReadinessSummary(
            status=readiness["status"],
            decisive_gaps=readiness["gaps"],
            blocker_codes=readiness["blockers"],
        ),
        next_action=choose_next_action(signals),
        allocation_preview=allocation,
        recent_activity=activity,
        pending_approvals_count=pending["approvals"],
        section_health=health,
    )
