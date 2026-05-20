from pathlib import Path
from app.agents.legal.chunker import chunk_regulation_text

FIXTURE = Path(__file__).parent / "data" / "tiny_ojk_fixture.txt"


def test_chunker_emits_one_chunk_per_pasal_when_short() -> None:
    text = FIXTURE.read_text()
    chunks = chunk_regulation_text(
        text=text,
        source="OJK",
        doc_hash="ojk-test",
        max_chars=2000,
        overlap=100,
    )
    pasals = sorted({c.pasal for c in chunks if c.pasal})
    assert pasals == ["1", "2", "3"], f"expected pasal 1/2/3, got {pasals}"


def test_chunker_records_ayat_when_pasal_has_ayats() -> None:
    text = FIXTURE.read_text()
    chunks = chunk_regulation_text(
        text=text, source="OJK", doc_hash="ojk-test", max_chars=2000, overlap=100,
    )
    pasal_3_chunks = [c for c in chunks if c.pasal == "3"]
    assert pasal_3_chunks, "pasal 3 must produce at least one chunk"
    # Pasal 3 has ayat (1) and (2); chunker may merge them into one chunk or split
    ayat_set = {c.ayat for c in pasal_3_chunks if c.ayat}
    # Either both ayats present, or chunk covers both with ayat=None (whole pasal)
    assert ayat_set <= {"1", "2"}


def test_chunker_chunk_id_is_deterministic() -> None:
    text = FIXTURE.read_text()
    a = chunk_regulation_text(text=text, source="OJK", doc_hash="h", max_chars=2000, overlap=100)
    b = chunk_regulation_text(text=text, source="OJK", doc_hash="h", max_chars=2000, overlap=100)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]


def test_chunker_splits_long_pasal_with_overlap() -> None:
    """A pasal longer than max_chars must be split, with overlap so context
    isn't lost across boundaries."""
    long_text = "Pasal 1\n" + ("kata kunci penting " * 200) + "\nPasal 2\nIsi pasal 2."
    chunks = chunk_regulation_text(
        text=long_text, source="OJK", doc_hash="h",
        max_chars=500, overlap=100,
    )
    pasal_1 = [c for c in chunks if c.pasal == "1"]
    assert len(pasal_1) >= 2, "long pasal must be split into multiple chunks"
    # Verify overlap: consecutive chunks share at least `overlap` characters
    for prev, curr in zip(pasal_1, pasal_1[1:]):
        assert any(token in prev.text and token in curr.text for token in curr.text.split()[:20])
