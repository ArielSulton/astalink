"""Static ticker→sector map.

Hackathon shortcut: hand-curated, not a full IDX listing (~900+ emiten).
Production would pull this from IDX's own sector classification (IDX-IC) or
a market data provider. Sector labels are informal groupings, NOT the
official IDX-IC taxonomy — the only labels load-bearing for correctness are
"tobacco" / "alcohol" / "gambling", since `sector_caps_from_citations`
(app/agents/optimizer/constraints.py) maps OJK regulatory keywords straight
to those three strings and relies on `sector_of()` agreeing with them."""
TICKER_SECTOR: dict[str, str] = {
    # Banking
    "BBCA": "banking",
    "BMRI": "banking",
    "BBNI": "banking",
    "BBRI": "banking",
    "BBTN": "banking",
    "BRIS": "banking",
    # Tobacco (the AstaLink rejection demo — must stay "tobacco", see above)
    "GGRM": "tobacco",
    "HMSP": "tobacco",
    "WIIM": "tobacco",
    # Alcohol (must stay "alcohol", see above)
    "MLBI": "alcohol",
    # Consumer / FMCG
    "INDF": "consumer",
    "ICBP": "consumer",
    "UNVR": "consumer",
    "MYOR": "consumer",
    "CPIN": "consumer",
    "JPFA": "consumer",
    "AMRT": "consumer",
    # Telco
    "TLKM": "telco",
    "EXCL": "telco",
    "ISAT": "telco",
    "FREN": "telco",
    # Mining & energy (coal/oil/gas/metals grouped together)
    "ANTM": "mining",
    "PTBA": "mining",
    "ADRO": "mining",
    "ITMG": "mining",
    "INCO": "mining",
    "MDKA": "mining",
    "PGAS": "mining",
    "MEDC": "mining",
    # Basic materials (cement)
    "SMGR": "basic_materials",
    "INTP": "basic_materials",
    # Property & real estate
    "BSDE": "property",
    "CTRA": "property",
    "PWON": "property",
    "SMRA": "property",
    # Infrastructure & construction
    "WIKA": "infrastructure",
    "WSKT": "infrastructure",
    "PTPP": "infrastructure",
    "JSMR": "infrastructure",
    # Healthcare
    "KLBF": "healthcare",
    "SIDO": "healthcare",
    "MIKA": "healthcare",
    # Technology & media
    "GOTO": "technology",
    "BUKA": "technology",
    "EMTK": "technology",
    "SCMA": "technology",
    # Industrials / conglomerate
    "ASII": "industrials",
    "MAPI": "industrials",
}


def sector_of(ticker: str) -> str:
    return TICKER_SECTOR.get(ticker, "other")


# Common Indonesian/English phrasings the intent LLM might extract into
# entities["sector"], normalized to the TICKER_SECTOR category strings above.
# Deliberately keyword-based (not an exhaustive taxonomy) — same "hackathon
# shortcut" spirit as TICKER_SECTOR itself.
_SECTOR_ALIASES: dict[str, str] = {
    "bank": "banking", "banking": "banking", "perbankan": "banking",
    "telco": "telco", "telekomunikasi": "telco", "telecom": "telco",
    "telecommunication": "telco", "telecommunications": "telco",
    "consumer": "consumer", "fmcg": "consumer", "konsumer": "consumer",
    "mining": "mining", "tambang": "mining", "energy": "mining", "energi": "mining",
    "coal": "mining", "batu bara": "mining", "oil and gas": "mining", "migas": "mining",
    "basic_materials": "basic_materials", "basic materials": "basic_materials",
    "semen": "basic_materials", "cement": "basic_materials",
    "property": "property", "properti": "property", "real estate": "property",
    "infrastructure": "infrastructure", "infrastruktur": "infrastructure",
    "construction": "infrastructure", "konstruksi": "infrastructure",
    "healthcare": "healthcare", "kesehatan": "healthcare",
    "pharma": "healthcare", "farmasi": "healthcare",
    "technology": "technology", "teknologi": "technology", "tech": "technology",
    "industrials": "industrials", "industri": "industrials",
    "tobacco": "tobacco", "rokok": "tobacco",
    "alcohol": "alcohol", "minuman keras": "alcohol",
}


def sector_to_tickers(sector: str, limit: int = 4) -> list[str]:
    """Resolve a free-text sector mention (as extracted by the intent LLM)
    to its real constituent tickers, so a stated sector with no exact ticker
    ("bank atau telco gitu") gets a genuine A1-A4 prescreen instead of
    Layer 0 silently falling back to the baseline stand-in for the stocks
    leg (see engine.py's `effective_stock_score`) — which produces a
    baseline-vs-baseline tie (an uninformative, always-50/50 split) no
    matter what the user actually asked for.

    Returns [] for anything unrecognized — this must stay narrower than a
    generic default basket; guessing tickers outside the stated sector would
    quietly answer a different question (see intent/node.py)."""
    canonical = _SECTOR_ALIASES.get(sector.strip().lower())
    if canonical is None:
        return []
    matches = [t for t, s in TICKER_SECTOR.items() if s == canonical]
    return matches[:limit]
