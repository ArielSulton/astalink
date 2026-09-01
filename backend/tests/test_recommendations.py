"""Hybrid stock recommendations: cosine similarity, sector vectors,
content score, user score, cold-start fallback, hybrid combine, and the
GET /api/v1/recommendations endpoint."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from app.core.recommendations import (
    _bare_ticker,
    _cosine_similarity,
    _sector_vectors_by_workspace,
)


def test_bare_ticker_strips_exchange_suffix():
    assert _bare_ticker("BBCA.JK") == "BBCA"
    assert _bare_ticker("bbca") == "BBCA"


def test_cosine_similarity_identical_vectors_is_one():
    v = {"banking": 0.6, "telco": 0.4}
    assert abs(_cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal_vectors_is_zero():
    a = {"banking": 1.0}
    b = {"telco": 1.0}
    assert _cosine_similarity(a, b) == 0.0


def test_cosine_similarity_empty_vector_is_zero():
    assert _cosine_similarity({}, {"banking": 1.0}) == 0.0


def test_sector_vectors_by_workspace_normalizes_and_groups():
    rows = [
        # ws-1: 100% banking (BBCA.JK, cost basis 10*1000)
        {"workspace_id": "ws-1", "ticker": "BBCA.JK", "quantity": 10, "avg_cost": 1000},
        # ws-2: half banking (BMRI), half telco (TLKM)
        {"workspace_id": "ws-2", "ticker": "BMRI.JK", "quantity": 5, "avg_cost": 1000},
        {"workspace_id": "ws-2", "ticker": "TLKM.JK", "quantity": 5, "avg_cost": 1000},
    ]
    fake_sb = MagicMock()
    fake_sb.table.return_value.select.return_value.execute.return_value = MagicMock(data=rows)

    vectors = _sector_vectors_by_workspace(fake_sb)

    assert vectors["ws-1"] == {"banking": 1.0}
    assert abs(vectors["ws-2"]["banking"] - 0.5) < 1e-9
    assert abs(vectors["ws-2"]["telco"] - 0.5) < 1e-9
