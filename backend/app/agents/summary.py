"""Summary Node (N9) — honest terminal replies for analysis-only intents.

EVALUATE_BUSINESS and RISK_REVIEW used to fall through the optimizer/legal
allocation loop, which has nothing to validate for them and ended in an
actively-wrong "alokasi ditolak secara legal" reply even though the analysis
itself succeeded. This node formats the analyst output already sitting in
`entities` (business_valuation / risk_metrics — both include a Gemini
narration produced by their node) into one user-facing message, so no extra
LLM call is needed. PORTFOLIO_STATUS gets an honest not-yet-available pointer
instead of a dead-end."""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from app.agents.intents import Intent
from app.agents.state import AgentState
from app.core.metrics import track_node_duration
from app.core.supabase_admin import get_admin_client
from app.core.wallet import get_workspace_balance

log = logging.getLogger(__name__)

PORTFOLIO_STATUS_MESSAGE = (
    "Ringkasan posisi portofolio lewat chat belum tersedia. "
    "Silakan buka halaman Asset View untuk melihat alokasi yang sudah disetujui, "
    "atau halaman Transactions untuk riwayat eksekusi."
)


def _fmt_rp(value: float) -> str:
    return f"Rp {value:,.0f}".replace(",", ".")


def _business_reply(state: AgentState) -> str:
    val: dict[str, Any] | None = state.get("entities", {}).get("business_valuation")
    if val:
        lines = [
            f"Valuasi {val.get('business_name', 'bisnis Anda')}: "
            f"estimasi nilai perusahaan (enterprise value) "
            f"{_fmt_rp(float(val.get('enterprise_value', 0)))} "
            f"— metode DCF, discount rate {float(val.get('discount_rate', 0)):.0%}, "
            f"terminal growth {float(val.get('terminal_growth', 0)):.0%}.",
        ]
        if val.get("narration"):
            lines.append("")
            lines.append(str(val["narration"]).strip())
        return "\n".join(lines)

    reasons = {e.get("reason") for e in state.get("errors", []) if e.get("node") == "business"}
    if "no_matching_business" in reasons:
        return (
            "Saya tidak menemukan bisnis yang cocok di workspace ini. "
            "Tambahkan bisnis beserta catatan keuangannya lebih dulu di menu Bisnis Saya, "
            "lalu minta valuasi lagi."
        )
    if "no_financial_records" in reasons:
        return (
            "Bisnisnya ketemu, tapi belum ada catatan keuangan (laba per tahun) untuk "
            "dihitung. Lengkapi catatan keuangannya di menu Bisnis Saya, lalu coba lagi."
        )
    return (
        "Maaf, valuasi bisnis belum bisa dihitung untuk permintaan ini. "
        "Pastikan bisnis dan catatan keuangannya sudah terdaftar di menu Bisnis Saya."
    )


def _risk_reply(state: AgentState) -> str:
    assessment: dict[str, Any] | None = state.get("entities", {}).get("risk_metrics")
    metrics = (assessment or {}).get("metrics") or {}
    weights: dict[str, float] = (assessment or {}).get("suggested_weights") or {}

    if not weights or metrics.get("var_95") is None:
        return (
            "Review risiko membutuhkan minimal satu ticker dengan riwayat harga yang cukup. "
            "Sebutkan sahamnya, misalnya: \"Review risiko portofolio dengan BBCA dan TLKM\"."
        )

    tickers = ", ".join(t.replace(".JK", "") for t in weights)
    lines = [f"Hasil review risiko untuk {tickers}:"]
    lines.append(f"- VaR 95% (harian): {float(metrics['var_95']):.2%}")
    if metrics.get("var_99") is not None:
        lines.append(f"- VaR 99% (harian): {float(metrics['var_99']):.2%}")
    if metrics.get("sharpe") is not None:
        lines.append(f"- Sharpe ratio (disetahunkan): {float(metrics['sharpe']):.2f}")
    if assessment.get("narration"):
        lines.append("")
        lines.append(str(assessment["narration"]).strip())
    return "\n".join(lines)


def _portfolio_status_reply(state: AgentState) -> str:
    workspace_id = state.get("_workspace_id")
    balance = get_workspace_balance(get_admin_client(), workspace_id) if workspace_id else None
    if balance is None:
        return PORTFOLIO_STATUS_MESSAGE
    return (
        f"Saldo kas workspace Anda saat ini: {_fmt_rp(balance)}. "
        "Ringkasan posisi/holdings lewat chat belum tersedia — silakan buka halaman "
        "Asset View untuk melihat alokasi yang sudah disetujui, atau halaman "
        "Transactions untuk riwayat eksekusi."
    )


@track_node_duration("n9_summary")
def summary_node(state: AgentState) -> AgentState:
    intent = state.get("intent")
    if intent == Intent.EVALUATE_BUSINESS.value:
        reply = _business_reply(state)
    elif intent == Intent.RISK_REVIEW.value:
        reply = _risk_reply(state)
    else:  # PORTFOLIO_STATUS (and any future direct-summary intent)
        reply = _portfolio_status_reply(state)

    return {"messages": [*state.get("messages", []), AIMessage(content=reply)]}
