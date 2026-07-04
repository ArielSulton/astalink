"""Risk Agent (N2c). Quantitative outputs come from numpy/scipy ONLY."""
from __future__ import annotations

import logging

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.market.yfinance_client import fetch_close_prices
from app.agents.risk.mvo import mean_variance_optimize
from app.agents.risk.schemas import RiskAssessment, RiskMetrics
from app.agents.risk.var import historical_var
from app.agents.state import AgentState
from app.core.gemini import extract_text, get_chat_model
from app.core.metrics import track_node_duration

log = logging.getLogger(__name__)

NARRATE_SYSTEM = """\
You are a risk analyst. Given numeric VaR/Sharpe/weights, write ONE short
paragraph (≤80 words) summarizing the risk picture in Indonesian. Do NOT
introduce numbers not in the input."""


def _returns(closes: np.ndarray) -> np.ndarray:
    return np.diff(np.log(closes))


@track_node_duration("n2c_risk")
def risk_node(state: AgentState) -> AgentState:
    tickers = state.get("entities", {}).get("tickers") or []
    if not tickers:
        return {"entities": {**state.get("entities", {}),
                             "risk_metrics": RiskAssessment().model_dump()}}

    series: dict[str, np.ndarray] = {}
    for t in tickers:
        c = fetch_close_prices(t)
        if len(c) < 30:
            log.warning("risk_node: insufficient data for %s", t)
            continue
        series[t] = c

    if not series:
        return {"entities": {**state.get("entities", {}),
                             "risk_metrics": RiskAssessment().model_dump()}}

    rets = {t: _returns(c) for t, c in series.items()}
    aligned = np.vstack([r[-min(len(r) for r in rets.values()):] for r in rets.values()])

    expected_returns = aligned.mean(axis=1) * 252
    cov = np.cov(aligned) * 252
    weights = mean_variance_optimize(
        expected_returns=expected_returns, cov=cov, risk_aversion=2.0,
    )

    portfolio_returns = (weights[:, None] * aligned).sum(axis=0)
    metrics = RiskMetrics(
        var_95=historical_var(portfolio_returns, confidence=0.95),
        var_99=historical_var(portfolio_returns, confidence=0.99),
        sharpe=(portfolio_returns.mean() / portfolio_returns.std(ddof=1) * np.sqrt(252))
                if portfolio_returns.std(ddof=1) else None,
    )

    llm = get_chat_model()
    body = f"VaR95={metrics.var_95:.4f}, VaR99={metrics.var_99:.4f}, Sharpe={metrics.sharpe}"
    narration = extract_text(llm.invoke([SystemMessage(content=NARRATE_SYSTEM),
                            HumanMessage(content=body)]).content)

    assessment = RiskAssessment(
        metrics=metrics,
        suggested_weights=dict(zip(series.keys(), [float(w) for w in weights])),
        narration=narration,
    )
    return {"entities": {**state.get("entities", {}),
                         "risk_metrics": assessment.model_dump()}}
