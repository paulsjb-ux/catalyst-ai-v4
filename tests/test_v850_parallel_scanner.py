from __future__ import annotations

import numpy as np
import pandas as pd

from engine import scanner


def _frame(seed: int, rows: int = 260) -> pd.DataFrame:
    values = np.linspace(100 + seed, 140 + seed, rows)
    return pd.DataFrame(
        {
            "Open": values - 0.5,
            "High": values + 1,
            "Low": values - 1,
            "Close": values,
            "Volume": np.arange(rows) + 100_000,
        },
        index=pd.date_range("2025-01-01", periods=rows, freq="B"),
    )


def test_parallel_and_serial_scans_are_equivalent():
    scanner.clear_indicator_cache()
    prices = {f"T{i:03}": _frame(i) for i in range(30)}
    serial = scanner.run_scan(prices, workers=1)
    scanner.clear_indicator_cache()
    parallel = scanner.run_scan(prices, workers=8)
    pd.testing.assert_frame_equal(serial, parallel)


def test_indicator_cache_reuses_unchanged_history(monkeypatch):
    scanner.clear_indicator_cache()
    calls = {"count": 0}
    original = scanner.enrich_price_frame

    def counted(frame):
        calls["count"] += 1
        return original(frame)

    monkeypatch.setattr(scanner, "enrich_price_frame", counted)
    prices = {"AAA": _frame(1)}
    scanner.run_scan(prices, workers=1)
    scanner.run_scan(prices, workers=1)
    assert calls["count"] == 1


def test_changed_last_close_invalidates_cache(monkeypatch):
    scanner.clear_indicator_cache()
    calls = {"count": 0}
    original = scanner.enrich_price_frame

    def counted(frame):
        calls["count"] += 1
        return original(frame)

    monkeypatch.setattr(scanner, "enrich_price_frame", counted)
    frame = _frame(1)
    scanner.run_scan({"AAA": frame}, workers=1)
    changed = frame.copy()
    changed.loc[changed.index[-1], "Close"] += 2
    scanner.run_scan({"AAA": changed}, workers=1)
    assert calls["count"] == 2


def test_scanner_skips_bad_symbol_without_stopping(monkeypatch):
    scanner.clear_indicator_cache()
    original = scanner._latest_indicator_row

    def sometimes_bad(ticker, frame):
        if ticker == "BAD":
            raise ValueError("bad data")
        return original(ticker, frame)

    monkeypatch.setattr(scanner, "_latest_indicator_row", sometimes_bad)
    result = scanner.run_scan(
        {"GOOD": _frame(1), "BAD": _frame(2)},
        workers=2,
    )
    assert list(result["ticker"]) == ["GOOD"]
