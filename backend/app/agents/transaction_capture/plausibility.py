"""Aggregate-level sanity check for a newly-extracted transaction, separate
from extract_node's own per-entry confidence gate. Never blocks on its
own — it only flags the confirmation card with a warning; the human
confirmation step is still the actual gate. See spec's "Plausibility
check" section."""
from __future__ import annotations

import logging
import statistics

from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)

HISTORY_WINDOW = 20
MIN_HISTORY_FOR_ZSCORE = 5
Z_SCORE_THRESHOLD = 3.0


def compute_plausibility_flag(*, business_id: str, type_: str, amount: float) -> bool:
    try:
        res = (
            get_admin_client().table("business_transactions")
            .select("amount")
            .eq("business_id", business_id)
            .eq("type", type_)
            .eq("status", "confirmed")
            .order("occurred_at", desc=True)
            .limit(HISTORY_WINDOW)
            .execute()
        )
    except Exception as exc:
        log.error("compute_plausibility_flag: query failed: %s", exc)
        return True  # can't verify — treat conservatively, same as too-little-history

    amounts = [float(r["amount"]) for r in (res.data or [])]
    if len(amounts) < MIN_HISTORY_FOR_ZSCORE:
        return True

    mean = statistics.mean(amounts)
    stdev = statistics.pstdev(amounts)
    if stdev == 0:
        return amount != mean
    return abs((amount - mean) / stdev) > Z_SCORE_THRESHOLD
