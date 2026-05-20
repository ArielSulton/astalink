"""Pasal-aware chunker for Indonesian regulatory text.

Splits text into chunks anchored on `Pasal N` boundaries. If a pasal body
exceeds `max_chars`, it is sub-split with overlap so a token near a chunk
boundary is still discoverable in both neighbors.

This is a one-pass scanner over the text; we deliberately don't build a full
parse tree because (a) Indonesian regulations have surprisingly inconsistent
formatting and (b) the chunker is only a discovery aid for retrieval — the
LLM Grader is what actually validates citations."""
from __future__ import annotations

import re

from app.agents.legal.schemas import Chunk

# Matches "Pasal 12" or "Pasal 12A" at start of line.
PASAL_RE = re.compile(r"^\s*Pasal\s+(\d+[A-Za-z]?)\s*$", re.MULTILINE)
# Matches "ayat (1)" mid-text.
AYAT_RE = re.compile(r"ayat\s*\((\d+)\)")


def _split_into_pasal_blocks(text: str) -> list[tuple[str | None, str]]:
    """Returns a list of (pasal, body) pairs. Text before the first Pasal
    marker is returned with pasal=None."""
    matches = list(PASAL_RE.finditer(text))
    if not matches:
        return [(None, text)]

    blocks: list[tuple[str | None, str]] = []
    if matches[0].start() > 0:
        blocks.append((None, text[: matches[0].start()].strip()))

    for i, m in enumerate(matches):
        pasal = m.group(1)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end() : end].strip()
        if body:
            blocks.append((pasal, body))
    return blocks


def _split_long_body(body: str, max_chars: int, overlap: int) -> list[str]:
    if len(body) <= max_chars:
        return [body]
    pieces: list[str] = []
    step = max_chars - overlap
    for start in range(0, len(body), step):
        pieces.append(body[start : start + max_chars])
        if start + max_chars >= len(body):
            break
    return pieces


def _pick_dominant_ayat(piece: str) -> str | None:
    """If the piece contains exactly one ayat reference, return it.
    Otherwise None (the chunk spans multiple ayats)."""
    found = AYAT_RE.findall(piece)
    return found[0] if len(set(found)) == 1 else None


def chunk_regulation_text(
    *,
    text: str,
    source: str,
    doc_hash: str,
    max_chars: int = 800,
    overlap: int = 100,
    page: int | None = None,
) -> list[Chunk]:
    """Splits text into pasal-anchored chunks.

    Chunk_id format: `{source}-{pasal or 'preamble'}-{ayat or '_'}-{page or '_'}-{idx}`
    so the same input text always produces the same ids."""
    chunks: list[Chunk] = []
    for pasal, body in _split_into_pasal_blocks(text):
        pieces = _split_long_body(body, max_chars=max_chars, overlap=overlap)
        for idx, piece in enumerate(pieces):
            ayat = _pick_dominant_ayat(piece)
            chunk_id = (
                f"{source}-{pasal or 'preamble'}-{ayat or '_'}-{page or '_'}-{idx}"
            )
            chunks.append(
                Chunk(
                    text=piece.strip(),
                    source=source,
                    pasal=pasal,
                    ayat=ayat,
                    page=page,
                    doc_hash=doc_hash,
                    chunk_id=chunk_id,
                )
            )
    return chunks
