from data.universe import get_default_universe, normalise_tickers

def test_normalise_tickers_removes_duplicates():
    assert normalise_tickers("aapl, msft, AAPL") == ["AAPL", "MSFT"]

def test_default_universe_limit():
    assert len(get_default_universe(5)) == 5
