from app.agents.optimizer.sectors import TICKER_SECTOR, sector_of, sector_to_tickers


def test_sector_of_known_ticker() -> None:
    assert sector_of("BBCA") == "banking"
    assert sector_of("TLKM") == "telco"


def test_sector_of_unknown_ticker_falls_back_to_other() -> None:
    assert sector_of("ZZZZ") == "other"


def test_sector_to_tickers_resolves_indonesian_and_english_aliases() -> None:
    bank_tickers = sector_to_tickers("bank")
    assert bank_tickers
    assert all(TICKER_SECTOR[t] == "banking" for t in bank_tickers)

    telco_tickers = sector_to_tickers("telekomunikasi")
    assert telco_tickers
    assert all(TICKER_SECTOR[t] == "telco" for t in telco_tickers)


def test_sector_to_tickers_is_case_and_whitespace_insensitive() -> None:
    assert sector_to_tickers("  Bank  ") == sector_to_tickers("bank")
    assert sector_to_tickers("BANKING") == sector_to_tickers("banking")


def test_sector_to_tickers_returns_empty_for_unmapped_sector() -> None:
    """Must stay narrower than a generic default basket — guessing tickers
    outside the stated sector would quietly answer a different question."""
    assert sector_to_tickers("perkebunan") == []


def test_sector_to_tickers_respects_limit() -> None:
    assert len(sector_to_tickers("banking", limit=2)) == 2
