"""Static ticker→sector map.

Hackathon shortcut: hand-curated for the demo universe. Production would pull
this from IDX's sector classification or a market data provider."""
TICKER_SECTOR: dict[str, str] = {
    # Banking
    "BBCA": "banking",
    "BMRI": "banking",
    "BBNI": "banking",
    "BBRI": "banking",
    # Consumer / Tobacco (the AstaLink rejection demo)
    "GGRM": "tobacco",
    "HMSP": "tobacco",
    "INDF": "consumer",
    "ICBP": "consumer",
    # Telco
    "TLKM": "telco",
    "EXCL": "telco",
    # Mining
    "ANTM": "mining",
    "PTBA": "mining",
}


def sector_of(ticker: str) -> str:
    return TICKER_SECTOR.get(ticker, "other")
