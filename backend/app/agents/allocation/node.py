"""L0 graph node — runs the Layer 0 decision flow before any stock work.

Sits between N1 (intent) and the analyst fan-out for allocation intents.
If Layer 0 says INSUFFICIENT_DATA or allocates 0% to stocks, the stock
engine never runs at all: this node appends the user-facing message itself
and the graph routes straight to END.

DB loading lives here; the decision flow itself is app/agents/allocation/
engine.py (pure, tested without Supabase).
"""
from __future__ import annotations

import logging

from langchain_core.messages import AIMessage

from app.agents.allocation.engine import run_layer0
from app.agents.allocation.schemas import (
    BusinessProfile,
    InvestorProfile,
    Layer0Result,
    Layer0Status,
)
from app.agents.intents import Intent
from app.agents.state import AgentState
from app.core.metrics import track_node_duration
from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)


def load_business_profile(workspace_id: str,
                          business_name: str | None) -> tuple[dict | None, BusinessProfile | None]:
    """Returns (business_row, intake_profile). A registered business without
    an intake profile yields an empty BusinessProfile (completeness 0) —
    honest, and it triggers the staged interrogation."""
    sb = get_admin_client()
    query = sb.table("businesses").select("id,name").eq("workspace_id", workspace_id)
    if business_name:
        query = query.ilike("name", f"%{business_name}%")
    rows = query.execute().data or []
    if len(rows) != 1:
        return None, None
    business = rows[0]
    res = (sb.table("business_intake_profiles").select("profile")
           .eq("business_id", business["id"]).limit(1).execute())
    raw = (res.data or [{}])[0].get("profile") or {}
    try:
        return business, BusinessProfile.model_validate(raw)
    except Exception as exc:
        log.error("layer0: invalid intake profile for %s: %s", business["id"], exc)
        return business, BusinessProfile()


def load_investor_profile(workspace_id: str) -> InvestorProfile:
    sb = get_admin_client()
    res = (sb.table("investor_profiles").select("profile")
           .eq("workspace_id", workspace_id).limit(1).execute())
    raw = (res.data or [{}])[0].get("profile") or {}
    try:
        return InvestorProfile.model_validate(raw)
    except Exception as exc:
        log.error("layer0: invalid investor profile for %s: %s", workspace_id, exc)
        return InvestorProfile()


def _format_terminal_message(result: Layer0Result) -> str:
    if result.status == Layer0Status.INSUFFICIENT_DATA:
        lines = [result.narration, ""]
        for q in result.questions:
            lines.append(f"• {q.question}")
        lines.append("")
        lines.append("Lengkapi juga profil bisnis di menu Bisnis Saya → Intake "
                     "agar evaluasi bisa lebih dalam.")
        return "\n".join(lines)

    # allocated, but 0% stocks — explain instead of silently stopping
    alloc = result.allocation
    lines = [
        "Hasil alokasi Layer 0 (kelayakan tujuan dana):",
        f"• Kas: {alloc.cash:.0%} | Saham: {alloc.stocks:.0%} | "
        f"Bisnis: {alloc.business:.0%}",
        f"• Keyakinan: {result.confidence_label} ({result.confidence}/100)",
    ]
    if alloc.stocks == 0:
        lines.append("")
        lines.append("Mesin analisis saham tidak dijalankan karena alokasi "
                     "saham 0%.")
    for f in result.veto_flags:
        lines.append(f"⛔ {f.reason}" if f.hard else f"⚠ {f.reason}")
    return "\n".join(lines)


ALLOCATION_INTENTS = (Intent.ALLOCATE_STOCKS.value, Intent.ALLOCATE_CAPITAL.value)


@track_node_duration("l0_allocation")
def layer0_node(state: AgentState) -> AgentState:
    workspace_id = state.get("_workspace_id")
    entities = state.get("entities", {})
    intent = state.get("intent")

    business_profile = None
    business_row = None
    if workspace_id:
        wants_business = (intent == Intent.ALLOCATE_CAPITAL.value
                          or entities.get("business_name"))
        if wants_business:
            business_row, business_profile = load_business_profile(
                workspace_id, entities.get("business_name"))
            if business_profile is None and intent == Intent.ALLOCATE_CAPITAL.value:
                # capital question with no identifiable business: interrogate
                # from zero rather than pretending the leg doesn't exist
                business_profile = BusinessProfile()
        investor = load_investor_profile(workspace_id)
    else:
        investor = InvestorProfile()

    result = run_layer0(investor, business_profile)

    update: AgentState = {
        "layer0_result": {
            **result.model_dump(),
            "business_id": (business_row or {}).get("id"),
            "business_name": (business_row or {}).get("name"),
        },
    }

    terminal = (result.status == Layer0Status.INSUFFICIENT_DATA
                or (result.allocation is not None and result.allocation.stocks == 0))
    if terminal:
        update["messages"] = [*state.get("messages", []),
                              AIMessage(content=_format_terminal_message(result))]
    return update
