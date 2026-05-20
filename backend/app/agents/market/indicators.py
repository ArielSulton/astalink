"""TA-Lib indicator wrappers. The LLM is forbidden from producing these
numbers — they always come through this module.

`talib` is imported lazily inside compute_indicators() so just importing this
module does not require the C library to be installed. Modules that depend
on this one (e.g. market.node, graph) can therefore be imported on dev
machines without TA-Lib; only test cases that actually call compute_indicators
need the wrapper installed."""
from __future__ import annotations

import numpy as np


def compute_indicators(close: np.ndarray) -> dict[str, np.ndarray]:
    """Compute the standard AstaLink indicator pack.

    Returns a dict of arrays aligned to the input close series. Indicator values
    that aren't computable (e.g. SMA20 on a 5-day series) are NaN at those
    positions — TA-Lib's documented behavior."""
    import talib  # lazy: only required when this function actually runs

    close = close.astype(np.float64)
    sma20 = talib.SMA(close, timeperiod=20)
    ema50 = talib.EMA(close, timeperiod=50)
    rsi14 = talib.RSI(close, timeperiod=14)
    macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)

    return {
        "sma20": sma20,
        "ema50": ema50,
        "rsi14": rsi14,
        "macd": macd,
        "macd_signal": macd_signal,
        "bb_upper": bb_upper,
        "bb_middle": bb_middle,
        "bb_lower": bb_lower,
    }
