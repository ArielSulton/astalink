"""Central configuration for the two-layer capital allocation engine.

Every weight and threshold used by Layer 0 (capital allocation: cash vs
stocks vs business) and Layer 1 (stock engine A1-A4) lives here — no magic
numbers inside agent logic. All values are UNCALIBRATED PLACEHOLDERS to be
tuned by backtest; treat them as config, not truth.

Layout:
- StockScoreWeights   — synthesizer formula weights (A1/A2/A3/A4)
- LiquidityGateConfig — A3 hard-gate thresholds (conservative/aggressive)
- NewsCredibilityConfig — A1 source-credibility weighting + priced-in rule
- CompletenessConfig  — B0 intake gate tiers
- EvidenceWeights     — VERIFIED/CLAIMED/ESTIMATED weighting in scoring
- ConstraintConfig    — L0-2 personal hard-veto thresholds
- QualityConfig       — L0-3 Q1 unit-economics rules
- AdjustmentConfig    — Layer 0 STEP 4 risk & time adjustment factors
- BaselineConfig      — the always-on-the-table boring alternative
- VerdictBands        — score → verdict band mapping
- StalenessConfig     — market-data freshness guardrail
"""
from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# Layer 1 — stock engine
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class StockScoreWeights:
    """base_score = a4_flow*w + a1_news*w + a2_macro*w + a3_quality*w.

    No adversarial discount layer — A5 does not exist; its hard gates are
    folded into A1 (credibility/priced-in/amplification) and A3
    (manipulation_risk)."""
    a1_news: float = 0.30
    a2_macro: float = 0.25
    a3_quality: float = 0.10
    a4_flow: float = 0.35


@dataclass(frozen=True)
class GateThresholds:
    """One A3 threshold profile. Values in IDR unless noted."""
    min_market_cap: float = 1_000_000_000_000          # Rp 1 T
    min_free_float_pct: float = 0.15
    min_avg_daily_value: float = 5_000_000_000         # Rp 5 B/day (20d)
    min_adv_to_position_ratio: float = 20.0
    max_bid_ask_spread_pct: float = 0.01
    exclude_special_monitoring: bool = True


@dataclass(frozen=True)
class LiquidityGateConfig:
    """A3 gate: two named profiles. Large market cap with tiny free float is
    MORE dangerous, not less — both are always checked."""
    conservative: GateThresholds = field(default_factory=GateThresholds)
    aggressive: GateThresholds = field(default_factory=lambda: GateThresholds(
        min_market_cap=500_000_000_000,                # Rp 500 B
    ))
    adv_window_days: int = 20
    # manipulation_risk signal thresholds
    volume_spike_ratio: float = 5.0        # today vs 20d avg with no news
    thin_float_pct: float = 0.10           # free float below this = "thin"
    limit_up_streak_days: int = 3          # consecutive ~ARA days
    limit_up_daily_gain_pct: float = 0.15  # daily gain counted as ~limit-up
    volume_collapse_ratio: float = 0.3     # post-streak volume vs streak avg


@dataclass(frozen=True)
class NewsCredibilityConfig:
    """A1 credibility weighting (folded-in A5 gate). IDX disclosure counts
    3x mainstream media, 6x forum/rumor."""
    weight_primary: float = 6.0     # IDX official disclosure
    weight_secondary: float = 2.0   # mainstream media (primary = 3x this)
    weight_rumor: float = 1.0       # forum / social / unattributed
    # already_priced_in: price moved more than this BEFORE publication
    priced_in_move_pct: float = 0.10
    priced_in_lookback_days: int = 5
    # coordinated_amplification: same story replicated across this many
    # low-quality outlets within the window
    amplification_min_copies: int = 3
    amplification_window_hours: int = 24


@dataclass(frozen=True)
class MacroConfig:
    """A2 — macro & regulation (Indonesia/IDX). Rule-based signals from
    index + FX trends; each component in [-1, 1], combined by weight into
    a 0-100 score (50 = neutral)."""
    ihsg_symbol: str = "^JKSE"
    fx_symbol: str = "USDIDR=X"     # rising = rupiah weakening = negative
    trend_sma_days: int = 50
    momentum_lookback_days: int = 63    # ~3 months of trading days
    ihsg_weight: float = 0.6
    fx_weight: float = 0.4
    # momentum saturates at ±this 3-month move
    momentum_saturation_pct: float = 0.10


# --------------------------------------------------------------------------
# Layer 0 — capital allocation
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class CompletenessConfig:
    """B0 intake gate. UNKNOWN fields never count as present."""
    insufficient_below: float = 0.40   # → INSUFFICIENT_DATA, stop
    partial_below: float = 0.70        # → proceed, confidence capped
    partial_confidence_cap: int = 50   # out of 100
    staged_questions_first_batch: int = 3


@dataclass(frozen=True)
class EvidenceWeights:
    """How much a field's value counts in scoring, by evidence tag.
    UNKNOWN is deliberately absent: an unknown value is never scored,
    never defaulted, never interpolated."""
    verified: float = 1.0
    claimed: float = 0.4
    estimated: float = 0.6


@dataclass(frozen=True)
class ConstraintConfig:
    """L0-2 hard-veto thresholds. Vetoes are absolute — no score overrides."""
    min_emergency_fund_months: float = 6.0
    min_horizon_months_for_business: float = 24.0
    max_business_pct_of_net_worth: float = 0.50
    consumer_debt_interest_veto_pct: float = 0.12
    min_operator_hours_per_week: float = 10.0


@dataclass(frozen=True)
class QualityConfig:
    """L0-3 Q1 unit-economics hard rules."""
    max_cac_to_ltv_ratio: float = 1 / 3    # CAC < LTV/3
    max_payback_months: float = 12.0


@dataclass(frozen=True)
class DevilsAdvocateConfig:
    """L0-4 DB1-DB7 finding severities → business-score penalty.
    business_score = f(Q1..Q5) × (1 − DB_penalty) × completeness_factor."""
    penalty_critical: float = 0.15
    penalty_warning: float = 0.07
    penalty_info: float = 0.0
    penalty_cap: float = 0.60
    # DB1: month-over-month growth above this, merely CLAIMED, is treated
    # as a hockey-stick projection
    hockey_stick_monthly_growth: float = 0.20
    # DB2: base-rate prior for 5-year small-business survival (Indonesia)
    base_rate_5yr_survival: float = 0.50


@dataclass(frozen=True)
class AdjustmentConfig:
    """Layer 0 STEP 4 risk & time adjustment.

    CRITICAL RULE (enforced in code): if control == 0 and info_edge == 0,
    both premiums collapse to 1.0 — the business has lost its only
    structural advantages."""
    illiquidity_discount_min: float = 0.6
    illiquidity_discount_max: float = 0.8
    control_premium_min: float = 1.0
    control_premium_max: float = 1.3
    info_edge_premium_min: float = 1.0
    info_edge_premium_max: float = 1.4
    # value of operator hours, IDR/hour, used for time_cost_of_user
    operator_hour_value_idr: float = 100_000.0


@dataclass(frozen=True)
class BaselineConfig:
    """The most boring alternative — always on the table (DB6)."""
    risk_free_annual_return: float = 0.065   # Indonesian govt bonds ~6-7%
    index_fund_annual_return: float = 0.08   # IHSG index fund proxy
    baseline_score: float = 50.0             # its fixed slot on the 0-100 scale


@dataclass(frozen=True)
class VerdictBands:
    """final_score → verdict band. Score is 0-100."""
    strong_buy_at: float = 80.0
    buy_at: float = 65.0
    watchlist_at: float = 50.0
    avoid_at: float = 35.0
    # below avoid_at → REJECT


@dataclass(frozen=True)
class SynthesizerConfig:
    """Layer 1 synthesizer: verdict mechanics beyond the raw bands."""
    # invalidation condition: thesis void if close drops this far below entry
    invalidation_stop_pct: float = 0.08
    default_horizon: str = "3-6 bulan"
    # a CONDITIONAL A3 gate caps the verdict at WATCHLIST
    conditional_gate_caps_at: str = "watchlist"
    # score renormalization needs at least this many known components
    min_known_components: int = 2


@dataclass(frozen=True)
class SplitConfig:
    """Layer 0 STEP 5: how adjusted scores map to a cash/stocks/business split."""
    min_cash_floor: float = 0.10
    # an option only earns allocation for the score margin above this floor
    score_floor: float = 30.0
    # without control AND without info edge, business must beat stocks by
    # this many points to receive any allocation at all
    no_edge_business_hurdle: float = 15.0


@dataclass(frozen=True)
class StalenessConfig:
    """Guardrail 1: market data older than this is flagged stale and
    excluded from gating decisions."""
    max_market_data_age_hours: float = 48.0
    max_news_age_days: float = 14.0


@dataclass(frozen=True)
class AllocationConfig:
    stock_weights: StockScoreWeights = field(default_factory=StockScoreWeights)
    gate: LiquidityGateConfig = field(default_factory=LiquidityGateConfig)
    news: NewsCredibilityConfig = field(default_factory=NewsCredibilityConfig)
    macro: MacroConfig = field(default_factory=MacroConfig)
    completeness: CompletenessConfig = field(default_factory=CompletenessConfig)
    evidence: EvidenceWeights = field(default_factory=EvidenceWeights)
    constraints: ConstraintConfig = field(default_factory=ConstraintConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    devils_advocate: DevilsAdvocateConfig = field(default_factory=DevilsAdvocateConfig)
    adjustment: AdjustmentConfig = field(default_factory=AdjustmentConfig)
    baseline: BaselineConfig = field(default_factory=BaselineConfig)
    verdict: VerdictBands = field(default_factory=VerdictBands)
    synthesizer: SynthesizerConfig = field(default_factory=SynthesizerConfig)
    split: SplitConfig = field(default_factory=SplitConfig)
    staleness: StalenessConfig = field(default_factory=StalenessConfig)
    gate_profile: str = "conservative"  # which GateThresholds profile A3 uses

    def active_gate_thresholds(self) -> GateThresholds:
        return getattr(self.gate, self.gate_profile)


allocation_config = AllocationConfig()
