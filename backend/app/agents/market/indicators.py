"""Indicator calculations using pandas — no C library required.

The LLM is forbidden from producing these numbers — they always come through
this module. All formulas match TA-Lib's documented defaults so indicator
values are numerically equivalent."""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_indicators(
    close: np.ndarray,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
    volume: np.ndarray | None = None,
    open_: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Compute the standard AstaLink indicator pack.

    Returns a dict of arrays aligned to the input close series. Indicator
    values that aren't computable (e.g. SMA20 on a 5-day series) are NaN
    at those positions — matching TA-Lib's documented behavior. Indicators
    that need data the caller didn't supply (VWAP/ATR/Stoch/OBV) are all-NaN.
    """
    s = pd.Series(close.astype(np.float64))
    n = len(s)

    def _series(arr: np.ndarray | None) -> pd.Series | None:
        if arr is None or len(arr) == 0:
            return None
        return pd.Series(arr.astype(np.float64), index=s.index)

    high_s = _series(high)
    low_s = _series(low)
    vol_s = _series(volume)
    open_s = _series(open_)

    # --- Trend / MA ---
    sma20 = s.rolling(window=20, min_periods=20).mean()
    ema9 = s.ewm(span=9, min_periods=9, adjust=False).mean()
    ema20 = s.ewm(span=20, min_periods=20, adjust=False).mean()
    ema50 = s.ewm(span=50, min_periods=50, adjust=False).mean()

    # --- Wilder's RSI (alpha = 1/14) — matches TA-Lib ---
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi14 = 100 - (100 / (1 + rs))
    rsi14 = rsi14.where(avg_loss != 0, other=100.0)
    rsi14 = rsi14.where(s.notna() & (s.index >= 14))

    # --- MACD (12, 26, 9) ---
    ema12 = s.ewm(span=12, min_periods=12, adjust=False).mean()
    ema26 = s.ewm(span=26, min_periods=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, min_periods=9, adjust=False).mean()
    macd_hist = macd - macd_signal

    # --- Bollinger Bands (20, 2) — population std to match TA-Lib ---
    bb_middle = sma20
    bb_std = s.rolling(window=20, min_periods=20).std(ddof=0)
    bb_upper = bb_middle + 2 * bb_std
    bb_lower = bb_middle - 2 * bb_std

    # --- ATR (14) — needs high+low ---
    atr14 = pd.Series(np.nan, index=s.index)
    if high_s is not None and low_s is not None:
        prev_close = s.shift(1)
        tr = pd.concat(
            [
                high_s - low_s,
                (high_s - prev_close).abs(),
                (low_s - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr14 = tr.ewm(alpha=1 / 14, adjust=False).mean()

    # --- Stochastic (14, 3) — needs high+low ---
    stoch_k = pd.Series(np.nan, index=s.index)
    stoch_d = pd.Series(np.nan, index=s.index)
    if high_s is not None and low_s is not None:
        llv = low_s.rolling(window=14, min_periods=14).min()
        hhv = high_s.rolling(window=14, min_periods=14).max()
        rng = (hhv - llv).replace(0, np.nan)
        stoch_k_raw = 100 * (s - llv) / rng
        stoch_k = stoch_k_raw
        stoch_d = stoch_k.rolling(window=3, min_periods=3).mean()

    # --- OBV — needs volume ---
    obv = pd.Series(np.nan, index=s.index)
    if vol_s is not None:
        direction = np.sign(s.diff().fillna(0))
        obv = (direction * vol_s).cumsum().astype(np.float64)

    # --- VWAP — needs volume + high + low + open ---
    vwap = pd.Series(np.nan, index=s.index)
    if vol_s is not None and high_s is not None and low_s is not None and open_s is not None:
        typical = (high_s + low_s + s) / 3.0
        cum_vp = (typical * vol_s).cumsum()
        cum_v = vol_s.cumsum().replace(0, np.nan)
        vwap = cum_vp / cum_v

    return {
        "sma20": sma20.to_numpy(),
        "ema9": ema9.to_numpy(),
        "ema20": ema20.to_numpy(),
        "ema50": ema50.to_numpy(),
        "rsi14": rsi14.to_numpy(),
        "macd": macd.to_numpy(),
        "macd_signal": macd_signal.to_numpy(),
        "macd_hist": macd_hist.to_numpy(),
        "bb_upper": bb_upper.to_numpy(),
        "bb_middle": bb_middle.to_numpy(),
        "bb_lower": bb_lower.to_numpy(),
        "atr14": atr14.to_numpy(),
        "stoch_k": stoch_k.to_numpy(),
        "stoch_d": stoch_d.to_numpy(),
        "obv": obv.to_numpy(),
        "vwap": vwap.to_numpy(),
    }