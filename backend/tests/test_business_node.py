from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from app.agents.business.node import business_node
from app.agents.state import new_state


def _mock_admin_client(businesses: list[dict], records: list[dict]) -> MagicMock:
    """Fake Supabase admin client: .table("businesses") and
    .table("business_financial_records") each return their own fluent
    query-builder mock ending in .execute() -> MagicMock(data=...)."""
    sb = MagicMock()

    businesses_query = MagicMock()
    businesses_query.select.return_value = businesses_query
    businesses_query.eq.return_value = businesses_query
    businesses_query.ilike.return_value = businesses_query
    businesses_query.execute.return_value = MagicMock(data=businesses)

    records_query = MagicMock()
    records_query.select.return_value = records_query
    records_query.eq.return_value = records_query
    records_query.order.return_value = records_query
    records_query.execute.return_value = MagicMock(data=records)

    def _table(name: str):
        return businesses_query if name == "businesses" else records_query

    sb.table.side_effect = _table
    return sb


def test_business_node_auto_picks_the_only_business_in_workspace() -> None:
    state = new_state()
    state["_workspace_id"] = "ws-1"

    fake_admin = _mock_admin_client(
        businesses=[{"id": "biz-1", "name": "Toko Maju Jaya"}],
        records=[{"period_year": 2023, "profit": 100_000.0},
                 {"period_year": 2024, "profit": 120_000.0}],
    )
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Valuasi positif.")

    with patch("app.agents.business.node.get_admin_client", return_value=fake_admin), \
         patch("app.agents.business.node.get_chat_model", return_value=fake_llm):
        update = business_node(state)

    val = update["entities"]["business_valuation"]
    assert val is not None
    assert val["business_name"] == "Toko Maju Jaya"
    assert val["enterprise_value"] > 0
    assert val["cashflows"] == [100_000.0, 120_000.0]
    assert val["narration"]


def test_business_node_disambiguates_by_business_name_when_multiple_exist() -> None:
    state = new_state()
    state["_workspace_id"] = "ws-1"
    state["entities"] = {"business_name": "Maju Jaya"}

    fake_admin = _mock_admin_client(
        businesses=[{"id": "biz-2", "name": "Toko Maju Jaya"}],
        records=[{"period_year": 2024, "profit": 50_000.0}],
    )
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Valuasi.")

    with patch("app.agents.business.node.get_admin_client", return_value=fake_admin), \
         patch("app.agents.business.node.get_chat_model", return_value=fake_llm):
        update = business_node(state)

    assert update["entities"]["business_valuation"] is not None


def test_business_node_returns_none_when_no_matching_business() -> None:
    state = new_state()
    state["_workspace_id"] = "ws-1"

    fake_admin = _mock_admin_client(businesses=[], records=[])
    with patch("app.agents.business.node.get_admin_client", return_value=fake_admin):
        update = business_node(state)

    assert update["entities"]["business_valuation"] is None
    assert any(e["reason"] == "no_matching_business" for e in update["errors"])


def test_business_node_returns_none_when_ambiguous_multiple_businesses_and_no_name_given() -> None:
    state = new_state()
    state["_workspace_id"] = "ws-1"

    fake_admin = _mock_admin_client(
        businesses=[{"id": "biz-1", "name": "Toko A"}, {"id": "biz-2", "name": "Toko B"}],
        records=[],
    )
    with patch("app.agents.business.node.get_admin_client", return_value=fake_admin):
        update = business_node(state)

    assert update["entities"]["business_valuation"] is None
    assert any(e["reason"] == "no_matching_business" for e in update["errors"])


def test_business_node_returns_none_when_no_financial_records() -> None:
    state = new_state()
    state["_workspace_id"] = "ws-1"

    fake_admin = _mock_admin_client(
        businesses=[{"id": "biz-1", "name": "Toko Maju Jaya"}],
        records=[],
    )
    with patch("app.agents.business.node.get_admin_client", return_value=fake_admin):
        update = business_node(state)

    assert update["entities"]["business_valuation"] is None
    assert any(e["reason"] == "no_financial_records" for e in update["errors"])


def test_business_node_returns_none_when_no_workspace_id() -> None:
    state = new_state()  # no _workspace_id set
    update = business_node(state)
    assert update["entities"]["business_valuation"] is None
