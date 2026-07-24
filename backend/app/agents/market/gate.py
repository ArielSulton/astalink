"""A3 — Market Cap & Liquidity Gate (+ manipulation_risk).

This is a GATE, not a score: a FAIL rejects the ticker no matter what the
other agents say. `manipulation_risk == HIGH` is likewise an automatic
REJECT (a hard gate folded in from the removed adversarial layer).

Two deliberate properties:
- Pure logic (`evaluate_gate`) is separated from I/O (`fetch_liquidity_data`)
  so the gate is testable without yfinance.
- UNKNOWN is honest: data yfinance cannot provide (IDX board/special
  notation, UMA/suspension history, shareholder dilution history, warrant
  unlock schedules) is reported as an explicit evidence gap and turns a
  would-be PASS into CONDITIONAL — it is never guessed.

Large market cap with a tiny free float is MORE dangerous, not less — the
market cap is illusory. Both are always checked independently.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.core.allocation_config import GateThresholds, allocation_config

log = logging.getLogger(__name__)


class GateStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"   # passes on known data, but with gaps


class ManipulationRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"    # → automatic REJECT


class GateCheck(BaseModel):
    name: str
    status: Literal["pass", "fail", "unknown"]
    detail: str
    threshold: str
    observed: str


class LiquidityData(BaseModel):
    """Raw inputs for the gate. None = genuinely unavailable (UNKNOWN)."""
    ticker: str
    market_cap: float | None = None
    free_float_pct: float | None = None
    avg_daily_value_20d: float | None = None      # IDR/day
    bid_ask_spread_pct: float | None = None
    board: str | None = None                       # not on yfinance → None
    daily_returns_20d: list[float] = Field(default_factory=list)
    daily_volumes_20d: list[float] = Field(default_factory=list)
    has_recent_fundamental_news: bool | None = None
    as_of: str = ""                                # ISO timestamp (guardrail 1)


class GateResult(BaseModel):
    ticker: str
    status: GateStatus
    manipulation_risk: ManipulationRisk
    manipulation_signals: list[str] = Field(default_factory=list)
    checks: list[GateCheck] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    as_of: str = ""
    stale: bool = False


def _check(name: str, observed: float | None, threshold: float,
           *, op: str, fmt: str = "{:,.0f}") -> GateCheck:
    thr_s = fmt.format(threshold)
    if observed is None:
        return GateCheck(name=name, status="unknown", threshold=thr_s,
                         observed="UNKNOWN",
                         detail=f"{name}: data tidak tersedia")
    ok = observed >= threshold if op == ">=" else observed <= threshold
    return GateCheck(
        name=name,
        status="pass" if ok else "fail",
        threshold=thr_s,
        observed=fmt.format(observed),
        detail=f"{name}: {fmt.format(observed)} vs ambang {op} {thr_s}",
    )


def _manipulation_risk(data: LiquidityData) -> tuple[ManipulationRisk, list[str]]:
    """Rule-based signals from available data. Signals that require IDX
    disclosures (UMA history, dilution track record, warrant unlocks) are
    reported as evidence gaps by the caller, not silently scored here."""
    cfg = allocation_config.gate
    signals: list[str] = []

    vols = data.daily_volumes_20d
    rets = data.daily_returns_20d

    spike = False
    if len(vols) >= 5:
        prior_avg = sum(vols[:-1]) / max(1, len(vols) - 1)
        spike = prior_avg > 0 and vols[-1] >= cfg.volume_spike_ratio * prior_avg

    thin_float = (data.free_float_pct is not None
                  and data.free_float_pct < cfg.thin_float_pct)

    # thin float + volume spike with NO fundamental news → classic pump setup
    if spike and thin_float and data.has_recent_fundamental_news is False:
        signals.append(
            f"Free float tipis ({data.free_float_pct:.0%}) + lonjakan volume "
            f"≥{cfg.volume_spike_ratio:.0f}× rata-rata tanpa berita fundamental")

    # consecutive ~limit-up days followed by volume collapse
    streak = 0
    for i, r in enumerate(rets):
        if r >= cfg.limit_up_daily_gain_pct:
            streak += 1
            if streak >= cfg.limit_up_streak_days and i + 1 < len(vols):
                streak_avg = sum(vols[i - streak + 1:i + 1]) / streak
                after = vols[i + 1]
                if streak_avg > 0 and after <= cfg.volume_collapse_ratio * streak_avg:
                    signals.append(
                        f"{streak} hari beruntun naik ≥"
                        f"{cfg.limit_up_daily_gain_pct:.0%} lalu volume kolaps")
                    break
        else:
            streak = 0

    if signals:
        return ManipulationRisk.HIGH, signals

    weak: list[str] = []
    if spike:
        weak.append("Lonjakan volume mendadak vs rata-rata 20 hari")
    if thin_float:
        weak.append(f"Free float tipis ({data.free_float_pct:.0%})")
    if weak:
        return ManipulationRisk.MEDIUM, weak
    return ManipulationRisk.LOW, []


def evaluate_gate(
    data: LiquidityData,
    planned_position_idr: float | None = None,
    thresholds: GateThresholds | None = None,
) -> GateResult:
    thr = thresholds or allocation_config.active_gate_thresholds()

    checks = [
        _check("market_cap", data.market_cap, thr.min_market_cap, op=">="),
        _check("free_float", data.free_float_pct, thr.min_free_float_pct,
               op=">=", fmt="{:.1%}"),
        _check("avg_daily_value_20d", data.avg_daily_value_20d,
               thr.min_avg_daily_value, op=">="),
        _check("bid_ask_spread", data.bid_ask_spread_pct,
               thr.max_bid_ask_spread_pct, op="<=", fmt="{:.2%}"),
    ]

    if planned_position_idr and data.avg_daily_value_20d is not None:
        ratio = data.avg_daily_value_20d / planned_position_idr
        checks.append(_check("adv_to_position", ratio,
                             thr.min_adv_to_position_ratio, op=">=",
                             fmt="{:.1f}x"))
    else:
        checks.append(GateCheck(
            name="adv_to_position", status="unknown",
            threshold=f"{thr.min_adv_to_position_ratio:.0f}x",
            observed="UNKNOWN",
            detail="adv_to_position: ukuran posisi belum diketahui"))

    evidence_gaps: list[str] = []
    if data.board is None and thr.exclude_special_monitoring:
        checks.append(GateCheck(
            name="board", status="unknown",
            threshold="Main/Development (bukan Special Monitoring)",
            observed="UNKNOWN",
            detail="board: papan pencatatan IDX tidak tersedia dari sumber data"))
        evidence_gaps.append("Papan pencatatan IDX / notasi khusus tidak terverifikasi")
    elif data.board is not None:
        is_special = "special" in data.board.lower() or "pemantauan" in data.board.lower()
        checks.append(GateCheck(
            name="board",
            status="fail" if (is_special and thr.exclude_special_monitoring) else "pass",
            threshold="bukan Special Monitoring",
            observed=data.board,
            detail=f"board: {data.board}"))

    # Signals the data source cannot provide — declared, never guessed.
    evidence_gaps += [
        "Riwayat suspensi/UMA tidak tersedia dari sumber data",
        "Riwayat dilusi pemegang saham pengendali tidak tersedia",
        "Jadwal konversi waran/MTN tidak tersedia",
    ]

    risk, signals = _manipulation_risk(data)

    # Staleness guardrail: gate decisions on old data are flagged.
    stale = False
    if data.as_of:
        try:
            age_h = (datetime.now(timezone.utc)
                     - datetime.fromisoformat(data.as_of)).total_seconds() / 3600
            stale = age_h > allocation_config.staleness.max_market_data_age_hours
        except ValueError:
            stale = True

    if risk == ManipulationRisk.HIGH:
        status = GateStatus.FAIL   # hard gate: automatic REJECT
    elif any(c.status == "fail" for c in checks):
        status = GateStatus.FAIL
    elif any(c.status == "unknown" for c in checks) or stale:
        status = GateStatus.CONDITIONAL
    else:
        status = GateStatus.PASS

    return GateResult(
        ticker=data.ticker,
        status=status,
        manipulation_risk=risk,
        manipulation_signals=signals,
        checks=checks,
        evidence_gaps=evidence_gaps,
        as_of=data.as_of,
        stale=stale,
    )


# --------------------------------------------------------------------------
# I/O — yfinance fetch (cached like yfinance_client)
# --------------------------------------------------------------------------

_CACHE_TTL = 300
_cache: dict[str, tuple[LiquidityData, float]] = {}


def fetch_liquidity_data(ticker: str,
                         has_recent_fundamental_news: bool | None = None) -> LiquidityData:
    """Best-effort fetch. Anything Yahoo can't provide stays None (UNKNOWN)."""
    import yfinance as yf

    from app.agents.market.yfinance_client import _normalize_idx_ticker

    yf_ticker = _normalize_idx_ticker(ticker)
    now = time.time()
    if (entry := _cache.get(yf_ticker)) and now - entry[1] < _CACHE_TTL:
        data = entry[0].model_copy()
        data.has_recent_fundamental_news = has_recent_fundamental_news
        return data

    window = allocation_config.gate.adv_window_days
    market_cap = free_float = adv = spread = None
    rets: list[float] = []
    vols: list[float] = []
    try:
        t = yf.Ticker(yf_ticker)
        info = t.info or {}
        market_cap = info.get("marketCap")
        shares = info.get("sharesOutstanding")
        float_shares = info.get("floatShares")
        if shares and float_shares:
            free_float = float_shares / shares
        bid, ask = info.get("bid"), info.get("ask")
        if bid and ask and bid > 0:
            spread = (ask - bid) / ((ask + bid) / 2)

        hist = t.history(period="3mo", auto_adjust=True)
        if not hist.empty and len(hist) >= 2:
            tail = hist.tail(window + 1)
            closes = tail["Close"].tolist()
            volumes = tail["Volume"].tolist()
            rets = [(closes[i] - closes[i - 1]) / closes[i - 1]
                    for i in range(1, len(closes)) if closes[i - 1]]
            vols = volumes[1:]
            daily_values = [v * c for v, c in zip(volumes[1:], closes[1:])]
            if daily_values:
                adv = sum(daily_values) / len(daily_values)
    except Exception as exc:
        log.error("gate: liquidity fetch failed for %s: %s", ticker, exc)

    data = LiquidityData(
        ticker=ticker,
        market_cap=market_cap,
        free_float_pct=free_float,
        avg_daily_value_20d=adv,
        bid_ask_spread_pct=spread,
        board=None,  # not available from Yahoo — honest UNKNOWN
        daily_returns_20d=rets,
        daily_volumes_20d=vols,
        has_recent_fundamental_news=has_recent_fundamental_news,
        as_of=datetime.now(timezone.utc).isoformat(),
    )
    _cache[yf_ticker] = (data, now)
    return data
