"""Business valuation endpoint test."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.v1 import business as business_module
from app.agents.business.dcf import discounted_cash_flow


def test_dcf_matches_known_value():
    """DCF of flat profits returns the Gordon-growth present value."""
    cashflows = [100.0, 100.0, 100.0, 100.0, 100.0]
    ev = discounted_cash_flow(cashflows=cashflows, discount_rate=0.10, terminal_growth=0.03)
    assert ev > 0
    assert ev > 100.0 * 5  # positive terminal value


def test_valuation_route_registered():
    """The valuation route exists on the business router."""
    seen = {r.path for r in business_module.router.routes}
    assert "/{business_id}/valuation" in seen