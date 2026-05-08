"""Value-at-Risk computations (numpy only)."""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


def historical_var(returns: np.ndarray, confidence: float = 0.95) -> float:
    if len(returns) == 0:
        raise ValueError("returns array must be non-empty")
    pct = (1 - confidence) * 100
    return float(-np.percentile(returns, pct))


def parametric_var(returns: np.ndarray, confidence: float = 0.95) -> float:
    if len(returns) == 0:
        raise ValueError("returns array must be non-empty")
    mu = float(np.mean(returns))
    sigma = float(np.std(returns, ddof=1))
    z = norm.ppf(confidence)
    return -(mu - z * sigma)
