from pathlib import Path
import pandas as pd

from engine import universe_builder


def test_local_sp500_fallback_has_broad_coverage():
    tickers = universe_builder.load_universe_csv(
        universe_builder.SP500_FALLBACK_PATH
    )
    assert len(tickers) >= 450


def test_requested_523_symbols_are_returned_without_live_web(monkeypatch):
    monkeypatch.setattr(
        universe_builder,
        "_read_html_tables",
        lambda url: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    selected = universe_builder.build_scan_universe(max_tickers=523)
    assert len(selected) == 523
    assert len(selected) == len(set(selected))


def test_source_priority_preserves_global_coverage(monkeypatch, tmp_path):
    global_path = tmp_path / "global.csv"
    pd.DataFrame({"ticker": ["7203.T", "ALV.DE", "AAPL"]}).to_csv(
        global_path,
        index=False,
    )
    monkeypatch.setattr(universe_builder, "GLOBAL_LIQUID_PATH", global_path)
    monkeypatch.setattr(
        universe_builder,
        "fetch_sp500_tickers",
        lambda: ["AAPL", "MSFT", "NVDA"],
    )
    selected = universe_builder.build_scan_universe(
        include_watchlist=False,
        include_nasdaq100=False,
        include_starter_large_universe=False,
        max_tickers=4,
    )
    assert selected == ["7203.T", "ALV.DE", "AAPL", "MSFT"]
