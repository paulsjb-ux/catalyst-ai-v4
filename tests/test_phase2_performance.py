from __future__ import annotations

import time
import pandas as pd

from data import market_data


def _frame(rows: int = 80) -> pd.DataFrame:
    return pd.DataFrame({"Close": range(rows), "Open": range(rows), "High": range(rows), "Low": range(rows), "Volume": range(rows)})


def test_failed_ticker_retries_run_concurrently(monkeypatch, tmp_path):
    monkeypatch.setattr(market_data, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(market_data, "_download_batch", lambda *args, **kwargs: {})

    def slow_download(ticker, period, interval):
        time.sleep(0.08)
        return _frame()

    monkeypatch.setattr(market_data, "_download_single", slow_download)
    started = time.perf_counter()
    result = market_data.download_history(["AAA", "BBB", "CCC", "DDD"], use_cache=False, retry_workers=4)
    elapsed = time.perf_counter() - started
    assert len(result.prices) == 4
    assert elapsed < 0.25


def test_app_routes_are_lazy_import_definitions():
    source = open("app.py", encoding="utf-8").read()
    assert '"Settings": ("ui.settings", "render_settings")' in source
    assert "from ui.settings import" not in source
    assert "import_module(module_name)" in source
