import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _fake_admin(*, owned: bool, balance: float = 1_000_000_000,
                holdings: list[dict] | None = None,
                realized: list[dict] | None = None,
                credit_ok: bool = True):
    """Fake service-role client covering the workspaces / holdings /
    transactions chains the portfolio router touches."""
    ws_q = MagicMock()
    # ownership: select("id").eq().eq().limit().execute()
    (ws_q.select.return_value.eq.return_value.eq.return_value
     .limit.return_value.execute.return_value) = MagicMock(
        data=[{"id": "ws-1"}] if owned else [])
    # balance: select("cash_balance").eq().limit().execute()
    (ws_q.select.return_value.eq.return_value.limit.return_value
     .execute.return_value) = MagicMock(data=[{"cash_balance": balance}])
    # credit: update().eq().eq().execute()
    (ws_q.update.return_value.eq.return_value.eq.return_value
     .execute.return_value) = MagicMock(
        data=[{"cash_balance": balance}] if credit_ok else [])

    hold_q = MagicMock()
    # portfolio list: select("*").eq().execute()
    hold_q.select.return_value.eq.return_value.execute.return_value = \
        MagicMock(data=holdings or [])
    # get_holding: select("*").eq().eq().limit().execute()
    (hold_q.select.return_value.eq.return_value.eq.return_value
     .limit.return_value.execute.return_value) = MagicMock(
        data=(holdings or [])[:1])

    tx_q = MagicMock()
    tx_q.select.return_value.eq.return_value.eq.return_value.execute.return_value = \
        MagicMock(data=realized or [])

    admin = MagicMock()
    admin.table.side_effect = lambda name: {
        "workspaces": ws_q, "holdings": hold_q, "transactions": tx_q,
    }[name]
    return admin


def test_get_portfolio_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/portfolio?workspace_id=ws-1")
    assert resp.status_code == 401


def test_get_portfolio_rejects_unowned_workspace(client: TestClient) -> None:
    admin = _fake_admin(owned=False)
    with patch("app.api.deps.verify_token", return_value={"sub": str(uuid.uuid4())}), \
         patch("app.api.v1.portfolio.get_admin_client", return_value=admin):
        resp = client.get("/api/v1/portfolio?workspace_id=ws-1",
                          headers={"Authorization": "Bearer x"})
    assert resp.status_code == 403


def test_get_portfolio_marks_to_market(client: TestClient) -> None:
    admin = _fake_admin(
        owned=True, balance=500_000,
        holdings=[{"ticker": "BBCA", "quantity": 100, "avg_cost": 9000}],
        realized=[{"realized_pnl": 12345}],
    )
    with patch("app.api.deps.verify_token", return_value={"sub": str(uuid.uuid4())}), \
         patch("app.api.v1.portfolio.get_admin_client", return_value=admin), \
         patch("app.api.v1.portfolio._last_price", return_value=10000):
        resp = client.get("/api/v1/portfolio?workspace_id=ws-1",
                          headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    body = resp.json()
    h = body["holdings"][0]
    assert h["market_value"] == 1_000_000        # 100 * 10000
    assert h["unrealized_pnl"] == 100_000        # 100 * (10000 - 9000)
    assert body["total_realized_pnl"] == 12345
    assert body["total_equity"] == 1_500_000     # cash 500k + mv 1.0m


def test_get_portfolio_price_unavailable_is_null_not_zero(client: TestClient) -> None:
    admin = _fake_admin(
        owned=True,
        holdings=[{"ticker": "BBCA", "quantity": 100, "avg_cost": 9000}],
    )
    with patch("app.api.deps.verify_token", return_value={"sub": str(uuid.uuid4())}), \
         patch("app.api.v1.portfolio.get_admin_client", return_value=admin), \
         patch("app.api.v1.portfolio._last_price", return_value=None):
        resp = client.get("/api/v1/portfolio?workspace_id=ws-1",
                          headers={"Authorization": "Bearer x"})
    body = resp.json()
    assert body["holdings"][0]["market_value"] is None
    assert body["total_equity"] is None


def test_sell_rejects_insufficient_quantity(client: TestClient) -> None:
    admin = _fake_admin(
        owned=True,
        holdings=[{"id": "h1", "ticker": "BBCA", "quantity": 100, "avg_cost": 9000}],
    )
    with patch("app.api.deps.verify_token", return_value={"sub": str(uuid.uuid4())}), \
         patch("app.api.v1.portfolio.get_admin_client", return_value=admin), \
         patch("app.api.v1.portfolio.verify_user_pin", return_value=None), \
         patch("app.api.v1.portfolio._last_price", return_value=10000):
        resp = client.post("/api/v1/portfolio/BBCA/sell?workspace_id=ws-1",
                           json={"quantity": 200, "pin": "123456"},
                           headers={"Authorization": "Bearer x"})
    assert resp.status_code == 400


def test_sell_success_books_realized_pnl(client: TestClient) -> None:
    admin = _fake_admin(
        owned=True, balance=500_000,
        holdings=[{"id": "h1", "ticker": "BBCA", "quantity": 100, "avg_cost": 9000}],
    )
    with patch("app.api.deps.verify_token", return_value={"sub": str(uuid.uuid4())}), \
         patch("app.api.v1.portfolio.get_admin_client", return_value=admin), \
         patch("app.api.v1.portfolio.verify_user_pin", return_value=None), \
         patch("app.api.v1.portfolio._last_price", return_value=10000):
        resp = client.post("/api/v1/portfolio/BBCA/sell?workspace_id=ws-1",
                           json={"quantity": 40, "pin": "123456"},
                           headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["realized_pnl"] == 40000        # 40 * (10000 - 9000)
    assert body["proceeds"] == 400000
    assert body["remaining_quantity"] == 60
