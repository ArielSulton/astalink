"""One cheap read of what the workspace actually holds.

N1 and the dead-end reply writer both need to talk about real money: a
message like "uang yang barusan masuk ini enaknya ke mana?" only resolves if
the classifier can see the balance and the last few captured transactions.
Before this module N1 was the only node that decided anything while seeing
nothing but the raw text, so an ordinary question dead-ended at a
clarification prompt while its answer sat in the database.

Every query here is best-effort. A failure yields an empty snapshot, never
an exception — a missing snapshot must degrade the reply, not break the run.

`business_transactions` has no workspace_id of its own (see migration
0016); it hangs off `businesses`, which is why the business rows are loaded
first and their ids drive the transaction query.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.core.supabase_admin import get_admin_client
from app.core.wallet import get_workspace_balance

log = logging.getLogger(__name__)

MAX_TRANSACTIONS = 5


def format_rupiah(value: float) -> str:
    return f"Rp {value:,.0f}".replace(",", ".")


class TransactionBrief(BaseModel):
    occurred_at: str
    amount: float
    type: str                        # 'income' | 'expense'
    source: str | None = None
    business_name: str | None = None


class HoldingBrief(BaseModel):
    ticker: str
    quantity: float


class BusinessBrief(BaseModel):
    name: str
    has_intake_profile: bool


class WorkspaceSnapshot(BaseModel):
    cash_balance: float | None = None
    recent_transactions: list[TransactionBrief] = Field(default_factory=list)
    holdings: list[HoldingBrief] = Field(default_factory=list)
    businesses: list[BusinessBrief] = Field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return (self.cash_balance is None
                and not self.recent_transactions
                and not self.holdings
                and not self.businesses)

    def render_for_prompt(self) -> str:
        """Compact Indonesian block for a prompt. Empty string when there is
        nothing to say, so callers skip the block entirely instead of
        shipping an empty heading."""
        if self.is_empty:
            return ""
        lines: list[str] = []
        if self.cash_balance is not None:
            lines.append(f"- Saldo kas: {format_rupiah(self.cash_balance)}")
        for t in self.recent_transactions:
            arah = "masuk" if t.type == "income" else "keluar"
            asal = f" dari {t.business_name}" if t.business_name else ""
            lines.append(
                f"- Transaksi {arah}{asal}: {format_rupiah(t.amount)} "
                f"({t.occurred_at[:10]})")
        if self.holdings:
            held = ", ".join(f"{h.ticker} {h.quantity:g}" for h in self.holdings)
            lines.append(f"- Saham dipegang: {held}")
        for b in self.businesses:
            status = "data intake lengkap" if b.has_intake_profile \
                else "belum ada data intake"
            lines.append(f"- Bisnis terdaftar: {b.name} ({status})")
        return "\n".join(lines)


def _load_balance(sb, workspace_id: str) -> float | None:
    try:
        return get_workspace_balance(sb, workspace_id)
    except Exception as exc:  # noqa: BLE001
        log.error("context_snapshot: balance load failed: %s", exc)
        return None


def _load_businesses(sb, workspace_id: str) -> tuple[list[BusinessBrief], dict[str, str]]:
    """Returns (briefs, {business_id: name}). The id->name map is what lets
    business_transactions rows name their business, since that table has no
    workspace_id to join on."""
    try:
        rows = (sb.table("businesses").select("id,name")
                .eq("workspace_id", workspace_id).execute().data) or []
    except Exception as exc:  # noqa: BLE001
        log.error("context_snapshot: businesses load failed: %s", exc)
        return [], {}

    names = {r["id"]: r["name"] for r in rows}
    with_profile: set[str] = set()
    if names:
        try:
            profiles = (sb.table("business_intake_profiles").select("business_id")
                        .in_("business_id", list(names)).execute().data) or []
            with_profile = {p["business_id"] for p in profiles}
        except Exception as exc:  # noqa: BLE001
            log.error("context_snapshot: intake profiles load failed: %s", exc)

    briefs = [BusinessBrief(name=name, has_intake_profile=bid in with_profile)
              for bid, name in names.items()]
    return briefs, names


def _load_transactions(sb, business_names: dict[str, str]) -> list[TransactionBrief]:
    if not business_names:
        return []
    try:
        rows = (sb.table("business_transactions")
                .select("occurred_at,amount,type,source,business_id")
                .in_("business_id", list(business_names))
                .eq("status", "confirmed")
                .order("occurred_at", desc=True)
                .limit(MAX_TRANSACTIONS).execute().data) or []
    except Exception as exc:  # noqa: BLE001
        log.error("context_snapshot: transactions load failed: %s", exc)
        return []
    return [
        TransactionBrief(
            occurred_at=str(r.get("occurred_at") or ""),
            amount=float(r.get("amount") or 0),
            type=str(r.get("type") or ""),
            source=r.get("source"),
            business_name=business_names.get(r.get("business_id")),
        )
        for r in rows
    ]


def _load_holdings(sb, workspace_id: str) -> list[HoldingBrief]:
    try:
        rows = (sb.table("holdings").select("ticker,quantity")
                .eq("workspace_id", workspace_id).execute().data) or []
    except Exception as exc:  # noqa: BLE001
        log.error("context_snapshot: holdings load failed: %s", exc)
        return []
    return [HoldingBrief(ticker=str(r["ticker"]),
                         quantity=float(r.get("quantity") or 0)) for r in rows]


def load_snapshot(workspace_id: str | None) -> WorkspaceSnapshot:
    """Best-effort. Never raises, never partially fails a caller."""
    if not workspace_id:
        return WorkspaceSnapshot()
    try:
        sb = get_admin_client()
    except Exception as exc:  # noqa: BLE001
        log.error("context_snapshot: admin client unavailable: %s", exc)
        return WorkspaceSnapshot()

    businesses, names = _load_businesses(sb, workspace_id)
    return WorkspaceSnapshot(
        cash_balance=_load_balance(sb, workspace_id),
        businesses=businesses,
        recent_transactions=_load_transactions(sb, names),
        holdings=_load_holdings(sb, workspace_id),
    )
