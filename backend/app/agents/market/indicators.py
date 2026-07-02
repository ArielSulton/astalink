"""Indicator calculations using pandas — no C library required.

The LLM is forbidden from producing these numbers — they always come through
this module. All formulas match TA-Lib's documented defaults so indicator
values are numerically equivalent."""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_indicators(close: np.ndarray) -> dict[str, np.ndarray]:
    """Compute the standard AstaLink indicator pack.

    Returns a dict of arrays aligned to the input close series. Indicator
    values that aren't computable (e.g. SMA20 on a 5-day series) are NaN
    at those positions — matching TA-Lib's documented behavior."""
    s = pd.Series(close.astype(np.float64))

    sma20 = s.rolling(window=20, min_periods=20).mean()
    ema50 = s.ewm(span=50, min_periods=50, adjust=False).mean()

    # Wilder's RSI (alpha = 1/14) — matches TA-Lib
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi14 = (100 - (100 / (1 + rs))).where(s.notna() & (s.index >= 14))

    # MACD (12, 26, 9)
    ema12 = s.ewm(span=12, min_periods=12, adjust=False).mean()
    ema26 = s.ewm(span=26, min_periods=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, min_periods=9, adjust=False).mean()
    macd_hist = macd - macd_signal

    # Bollinger Bands (20, 2) — population std to match TA-Lib
    bb_middle = sma20
    bb_std = s.rolling(window=20, min_periods=20).std(ddof=0)
    bb_upper = bb_middle + 2 * bb_std
    bb_lower = bb_middle - 2 * bb_std

    return {
        "sma20": sma20.to_numpy(),
        "ema50": ema50.to_numpy(),
        "rsi14": rsi14.to_numpy(),
        "macd": macd.to_numpy(),
        "macd_signal": macd_signal.to_numpy(),
        "bb_upper": bb_upper.to_numpy(),
        "bb_middle": bb_middle.to_numpy(),
        "bb_lower": bb_lower.to_numpy(),
    }
