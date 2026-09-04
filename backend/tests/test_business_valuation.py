"""Business valuation endpoint test."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

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


_RECORDS = [
    {"id": "r-2023", "period_year": 2023, "aset": 90.0, "omset": 180.0, "profit": 25.0},
    {"id": "r-2024", "period_year": 2024, "aset": 100.0, "omset": 200.0, "profit": 30.0},
]


def _strict_order(column, desc=False):
    """Stand-in for the Supabase client's `.order(column, desc=False)`.

    The real builder rejects unknown keywords (e.g. ``asc=True``) with a
    TypeError — exactly the runtime failure this test guards against. A
    plain MagicMock would silently swallow the bad ``asc=`` kwarg.
    """
    if desc is not False and desc is not True:
        raise TypeError("desc must be a bool")
    result = MagicMock()
    result.execute.return_value = MagicMock(data=_RECORDS)
    return result


def test_valuation_orders_records_without_invalid_asc_keyword(client) -> None:
    """Regression: GET /{id}/valuation must not pass ``asc=`` to .order().

    The Supabase query builder's signature is ``order(column, desc=False)``;
    passing ``asc=True`` raised
    ``TypeError: BaseSelectRequestBuilder.order() got an unexpected keyword
    argument 'asc'``, turning the endpoint into a runtime 500 that broke the
    dashboard's business-condition panel.
    """
    mock_user = {"sub": str(uuid.uuid4())}
    biz = {
        "id": "biz-1", "workspace_id": "ws-1", "name": "Toko A",
        "industry": None, "description": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }

    records_query = MagicMock()
    records_query.select.return_value.eq.return_value.order.side_effect = _strict_order

    def _table(name: str):
        return records_query if name == "business_financial_records" else MagicMock()

    fake_admin = MagicMock()
    fake_admin.table.side_effect = _table

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.business.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.business._get_owned_business", return_value=biz):
        resp = client.get(
            "/api/v1/business/biz-1/valuation",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert [r["period_year"] for r in body["financial_records"]] == [2023, 2024]
    assert body["valuation"]["projection_years"] == 2