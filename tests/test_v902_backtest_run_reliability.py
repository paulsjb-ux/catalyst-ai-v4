from datetime import datetime, timezone
import pandas as pd

from data.market_data import MarketDataResult


def test_market_data_result_supports_stale_cache_count():
    result = MarketDataResult(
        prices={},
        errors={},
        fetched_at=datetime.now(timezone.utc),
        cache_hits=2,
        stale_cache_hits=3,
    )
    assert result.stale_cache_hits == 3


def test_backtesting_page_has_visible_failure_handling():
    source = open("ui/backtesting.py", encoding="utf-8").read()
    assert "No historical price data loaded" in source
    assert "Backtest could not run" in source
    assert "Price Data Loaded" in source
    assert "stale_cache_hits" in source


def test_empty_market_data_is_not_silently_presented_as_success():
    source = open("ui/backtesting.py", encoding="utf-8").read()
    assert "if loaded == 0" in source
    assert "raise RuntimeError" in source
