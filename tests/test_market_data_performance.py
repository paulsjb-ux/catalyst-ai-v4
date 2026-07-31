import pandas as pd

from data import market_data


def _frame(rows=80):
    return pd.DataFrame({"Close": range(rows), "Volume": range(rows)})


def test_download_history_deduplicates_and_batches(monkeypatch, tmp_path):
    monkeypatch.setattr(market_data, "CACHE_DIR", tmp_path)
    calls = []

    def fake_batch(tickers, period, interval):
        calls.append(list(tickers))
        return {ticker: _frame() for ticker in tickers}

    monkeypatch.setattr(market_data, "_download_batch", fake_batch)
    result = market_data.download_history(["aapl", "AAPL", "msft"], use_cache=False, batch_size=80)
    assert set(result.prices) == {"AAPL", "MSFT"}
    assert calls == [["AAPL", "MSFT"]]


def test_failed_batch_symbol_retries_individually(monkeypatch, tmp_path):
    monkeypatch.setattr(market_data, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(market_data, "_download_batch", lambda tickers, period, interval: {"AAPL": _frame()})
    monkeypatch.setattr(market_data, "_download_single", lambda ticker, period, interval: _frame())
    result = market_data.download_history(["AAPL", "MSFT"], use_cache=False)
    assert set(result.prices) == {"AAPL", "MSFT"}
