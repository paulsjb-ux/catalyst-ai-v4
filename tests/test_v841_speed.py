from datetime import datetime, timezone
import time
import pandas as pd
from data import market_data

def test_memory_cache_returns_shallow_copy():
    market_data._MEMORY_CACHE.clear()
    frame = pd.DataFrame({"Close": range(80)})
    market_data._MEMORY_CACHE[("AAA", "1y", "1d")] = (time.monotonic() + 60, frame)
    loaded = market_data._read_cache("AAA", "1y", "1d", 20)
    assert loaded is not frame
    assert loaded.equals(frame)

def test_atomic_cache_write(monkeypatch, tmp_path):
    monkeypatch.setattr(market_data, "CACHE_DIR", tmp_path)
    market_data._MEMORY_CACHE.clear()
    frame = pd.DataFrame({"Close": range(80)})
    market_data._write_cache("AAA", "1y", "1d", frame, datetime.now(timezone.utc), 5)
    loaded = market_data._read_cache("AAA", "1y", "1d", 5)
    assert loaded is not None
    assert len(loaded) == 80

def test_parallel_batch_option(monkeypatch):
    monkeypatch.setattr(
        market_data,
        "_download_batch",
        lambda tickers, period, interval: {
            ticker: pd.DataFrame({"Close": range(80)}) for ticker in tickers
        },
    )
    monkeypatch.setattr(market_data, "_write_cache", lambda *args, **kwargs: None)
    result = market_data.download_history(
        ["AAA", "BBB", "CCC"],
        batch_size=1,
        use_cache=False,
        batch_workers=2,
    )
    assert set(result.prices) == {"AAA", "BBB", "CCC"}
    assert result.errors == {}
