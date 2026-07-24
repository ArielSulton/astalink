"""Layer 1 synthesizer — per-ticker verdict from A1-A4.

    base_score  = (A4 × w4) + (A1 × w1) + (A2 × w2) + (A3_quality × w3)
    final_score = base_score        # no adversarial discount layer

Weights come from config (uncalibrated placeholders). Mechanics:
- A3 is primarily a GATE: FAIL → REJECT outright, whatever the score.
  Its *quality* contribution (the small w3 slice) is the pass-ratio of its
  checks. A CONDITIONAL gate caps the verdict at WATCHLIST.
- A component whose score is None (data unavailable) is EXCLUDED and the
  remaining weights renormalized — never defaulted to neutral. Fewer than
  min_known_components known → no verdict, evidence gaps say why.
- Every verdict carries an invalidation condition with a concrete price
  level: a recommendation with no stated condition under which it becomes
  wrong is not analysis.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.agents.market.flow import FlowScore
from app.agents.market.gate import GateResult, GateStatus
from app.agents.market.macro import MacroScore
from app.agents.market.news_scoring import NewsScore
from app.core.allocation_config import allocation_config


class VerdictBand(StrEnum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WATCHLIST = "watchlist"
    AVOID = "avoid"
    REJECT = "reject"
    NO_VERDICT = "no_verdict"   # too little data — a valid output


class StockVerdict(BaseModel):
    ticker: str
    band: VerdictBand
    score: float | None = None
    horizon: str = ""
    invalidation_condition: str = ""
    components: dict[str, float | None] = Field(default_factory=dict)
    gate_status: str = ""
    manipulation_risk: str = ""
    evidence_gaps: list[str] = Field(default_factory=list)
    detail: list[str] = Field(default_factory=list)
    as_of: str = ""


def _gate_quality(gate: GateResult) -> float | None:
    """Pass-ratio of evaluable gate checks × 100 (the w3 score slice)."""
    known = [c for c in gate.checks if c.status != "unknown"]
    if not known:
        return None
    return 100.0 * sum(1 for c in known if c.status == "pass") / len(known)


def _band_for(score: float) -> VerdictBand:
    bands = allocation_config.verdict
    if score >= bands.strong_buy_at:
        return VerdictBand.STRONG_BUY
    if score >= bands.buy_at:
        return VerdictBand.BUY
    if score >= bands.watchlist_at:
        return VerdictBand.WATCHLIST
    if score >= bands.avoid_at:
        return VerdictBand.AVOID
    return VerdictBand.REJECT


_BAND_ORDER = [VerdictBand.REJECT, VerdictBand.AVOID, VerdictBand.WATCHLIST,
               VerdictBand.BUY, VerdictBand.STRONG_BUY]


def synthesize(
    ticker: str,
    news: NewsScore,
    macro: MacroScore,
    gate: GateResult,
    flow: FlowScore,
    last_close: float | None = None,
    as_of: str = "",
) -> StockVerdict:
    cfg = allocation_config
    w = cfg.stock_weights
    syn = cfg.synthesizer

    a3_quality = _gate_quality(gate)
    components: dict[str, float | None] = {
        "a1_news": news.score,
        "a2_macro": macro.score,
        "a3_quality": a3_quality,
        "a4_flow": flow.score,
    }
    evidence_gaps = list(dict.fromkeys(gate.evidence_gaps + flow.evidence_gaps))
    detail = news.detail + macro.detail + flow.detail

    # Invalidation condition — concrete, price-anchored when possible.
    if last_close:
        stop = last_close * (1 - syn.invalidation_stop_pct)
        invalidation = (
            f"Tesis batal jika harga penutupan turun ke bawah Rp {stop:,.0f} "
            f"(-{syn.invalidation_stop_pct:.0%} dari Rp {last_close:,.0f}), "
            "atau jika muncul sinyal manipulasi / notasi khusus IDX baru.")
    else:
        invalidation = ("Tesis batal jika harga turun "
                        f"{syn.invalidation_stop_pct:.0%} dari level masuk, atau "
                        "jika muncul sinyal manipulasi / notasi khusus IDX baru.")

    # Hard gate first: A3 FAIL (incl. manipulation HIGH) → REJECT, no score.
    if gate.status == GateStatus.FAIL:
        return StockVerdict(
            ticker=ticker, band=VerdictBand.REJECT, score=None,
            horizon=syn.default_horizon,
            invalidation_condition="—", components=components,
            gate_status=gate.status.value,
            manipulation_risk=gate.manipulation_risk.value,
            evidence_gaps=evidence_gaps,
            detail=detail + [f"Gate A3 FAIL: "
                             + "; ".join(c.detail for c in gate.checks
                                         if c.status == "fail")
                             + ("; " + "; ".join(gate.manipulation_signals)
                                if gate.manipulation_signals else "")],
            as_of=as_of)

    weight_by_name = {"a1_news": w.a1_news, "a2_macro": w.a2_macro,
                      "a3_quality": w.a3_quality, "a4_flow": w.a4_flow}
    known = {k: v for k, v in components.items() if v is not None}
    if len(known) < syn.min_known_components:
        return StockVerdict(
            ticker=ticker, band=VerdictBand.NO_VERDICT, score=None,
            horizon=syn.default_horizon, invalidation_condition="—",
            components=components, gate_status=gate.status.value,
            manipulation_risk=gate.manipulation_risk.value,
            evidence_gaps=evidence_gaps + [
                f"Hanya {len(known)}/4 komponen punya data — tidak cukup "
                "untuk verdict"],
            detail=detail, as_of=as_of)

    total_w = sum(weight_by_name[k] for k in known)
    base_score = sum(v * weight_by_name[k] for k, v in known.items()) / total_w
    final_score = base_score   # no adversarial discount layer

    missing = [k for k, v in components.items() if v is None]
    if missing:
        evidence_gaps.append(
            "Komponen tanpa data (bobot direnormalisasi): " + ", ".join(missing))

    band = _band_for(final_score)
    if gate.status == GateStatus.CONDITIONAL:
        cap = VerdictBand(syn.conditional_gate_caps_at)
        if _BAND_ORDER.index(band) > _BAND_ORDER.index(cap):
            band = cap
            detail = detail + ["Verdict dibatasi WATCHLIST: gate A3 CONDITIONAL "
                               "(ada data yang tidak terverifikasi)"]

    return StockVerdict(
        ticker=ticker, band=band, score=round(final_score, 1),
        horizon=syn.default_horizon, invalidation_condition=invalidation,
        components=components, gate_status=gate.status.value,
        manipulation_risk=gate.manipulation_risk.value,
        evidence_gaps=evidence_gaps, detail=detail, as_of=as_of)
