from engine.universe_builder import build_scan_universe, clean_ticker, load_universe_csv, GLOBAL_LIQUID_PATH

def test_exchange_suffixes_are_preserved():
    assert clean_ticker("SHEL.L") == "SHEL.L"
    assert clean_ticker("ASML.AS") == "ASML.AS"
    assert clean_ticker("BRK.B") == "BRK-B"

def test_global_universe_is_large_and_diverse():
    tickers=load_universe_csv(GLOBAL_LIQUID_PATH)
    assert len(tickers) >= 250
    assert "SPY" in tickers
    assert "SHEL.L" in tickers
    assert "7203.T" in tickers
    assert "2330.TW" in tickers

def test_default_build_includes_global_markets():
    tickers=build_scan_universe(include_sp500=False, include_nasdaq100=False, include_watchlist=False, include_starter_large_universe=False)
    assert len(tickers) >= 250
