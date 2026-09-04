import pytest
from pydantic import ValidationError

from app.agents.transaction_capture.schemas import TransactionExtraction


def test_transaction_extraction_accepts_a_valid_income_entry() -> None:
    ext = TransactionExtraction(
        is_transaction=True, item_description="Nasi goreng", amount=15000.0,
        type="income", confidence=0.9, raw_input="jual nasi goreng 15rb",
    )
    assert ext.amount == 15000.0
    assert ext.type == "income"


def test_transaction_extraction_allows_null_fields_for_a_non_transaction() -> None:
    ext = TransactionExtraction(
        is_transaction=False, item_description=None, amount=None,
        type=None, confidence=0.1, raw_input="halo apa kabar",
    )
    assert ext.is_transaction is False
    assert ext.amount is None


def test_transaction_extraction_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        TransactionExtraction(
            is_transaction=True, item_description="x", amount=1.0,
            type="income", confidence=1.5, raw_input="x",
        )


def test_transaction_extraction_rejects_invalid_type_literal() -> None:
    with pytest.raises(ValidationError):
        TransactionExtraction(
            is_transaction=True, item_description="x", amount=1.0,
            type="refund", confidence=0.9, raw_input="x",
        )
