"""Discounted Cash Flow model — pure numpy/python, no LLM.

Standard 2-stage DCF: explicit cashflows for N years + terminal value via
Gordon growth model, discounted back to present at `discount_rate`."""
from __future__ import annotations

import numpy as np


def discounted_cash_flow(
    *,
    cashflows: list[float],
    discount_rate: float,
    terminal_growth: float,
) -> float:
    if discount_rate <= terminal_growth:
        raise ValueError(
            "discount_rate must be greater than terminal_growth (Gordon model)"
        )
    cf = np.asarray(cashflows, dtype=np.float64)
    n = len(cf)
    years = np.arange(1, n + 1)
    pv_explicit = float(np.sum(cf / (1 + discount_rate) ** years))

    # Gordon-growth terminal value is undefined/meaningless when the base
    # cashflow is non-positive: a perpetuity of losses has no finite value
    # floor and would produce a large negative terminal value that dwarfs the
    # explicit-period PV.  The real-world worst case is bankruptcy (EV → 0),
    # not minus-infinity — so we clamp to 0.  The explicit-period cashflows
    # (which already contain the loss year) still flow through pv_explicit
    # unaffected, giving a conservative but non-absurd result.
    if cf[-1] <= 0:
        terminal_value = 0.0
    else:
        terminal_value = float(cf[-1]) * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1 + discount_rate) ** n
    return pv_explicit + pv_terminal
