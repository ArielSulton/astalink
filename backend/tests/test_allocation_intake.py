"""B0 intake: evidence tags, completeness gate, staged interrogation."""
from __future__ import annotations

from app.agents.allocation.intake import (
    REQUIRED_FIELDS,
    completeness_tier,
    compute_completeness,
    missing_questions,
)
from app.agents.allocation.schemas import (
    BusinessProfile,
    BusinessStage,
    CompletenessTier,
    EvidenceTag,
    Tagged,
)


def _empty() -> BusinessProfile:
    return BusinessProfile()


def _mostly_filled() -> BusinessProfile:
    """Fill every required field except a couple, with CLAIMED evidence."""
    p = BusinessProfile()
    for name, _ in p.iter_fields():
        block_name, field_name = name.split(".")
        block = getattr(p, block_name)
        setattr(block, field_name,
                Tagged(value=1, evidence=EvidenceTag.CLAIMED))
    return p


def test_empty_profile_completeness_zero():
    assert compute_completeness(_empty()) == 0.0


def test_unknown_never_counts_as_present():
    p = _empty()
    # explicitly set a value but leave tag UNKNOWN — must not count
    p.cash.cash_on_hand = Tagged(value=100.0, evidence=EvidenceTag.UNKNOWN)
    assert compute_completeness(p) == 0.0


def test_full_profile_completeness_one():
    assert compute_completeness(_mostly_filled()) == 1.0


def test_tiers():
    assert completeness_tier(0.0) == CompletenessTier.INSUFFICIENT
    assert completeness_tier(0.39) == CompletenessTier.INSUFFICIENT
    assert completeness_tier(0.40) == CompletenessTier.PARTIAL
    assert completeness_tier(0.70) == CompletenessTier.PARTIAL
    assert completeness_tier(0.71) == CompletenessTier.OK


def test_staged_interrogation_first_batch_is_three_high_signal():
    qs = missing_questions(_empty())
    assert len(qs) == 3
    assert all(q.priority == 1 for q in qs)
    fields = {q.field for q in qs}
    # the three highest-signal questions per spec
    assert fields == {"current_state.stage", "capital_need.breakdown",
                      "deal_structure.instrument"}


def test_interrogation_moves_past_stage_one_when_answered():
    p = _empty()
    p.current_state.stage = Tagged(value=BusinessStage.EARLY_REVENUE,
                                   evidence=EvidenceTag.CLAIMED)
    p.capital_need.breakdown = Tagged(value=[], evidence=EvidenceTag.CLAIMED)
    p.deal_structure.instrument = Tagged(value="equity",
                                         evidence=EvidenceTag.CLAIMED)
    qs = missing_questions(p)
    assert qs, "later-stage questions should surface"
    assert all(q.priority >= 2 for q in qs)


def test_every_required_field_has_a_question():
    from app.agents.allocation.intake import _QUESTIONS
    missing = set(REQUIRED_FIELDS) - set(_QUESTIONS)
    assert not missing, f"required fields without a question: {missing}"


def test_required_fields_exist_on_schema():
    valid = {name for name, _ in BusinessProfile().iter_fields()}
    bad = set(REQUIRED_FIELDS) - valid
    assert not bad, f"REQUIRED_FIELDS not on schema: {bad}"
