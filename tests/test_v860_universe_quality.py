import pandas as pd
from data import universe_health
from engine import universe_builder

def test_broad_us_universe_is_large_and_filtered():
    frame = pd.read_csv(universe_builder.BROAD_US_PATH)
    assert len(frame) >= 3000
    names = frame["name"].str.lower()
    for bad in ["warrant", "acquisition", "exchange-traded note", "exchange traded note"]:
        assert not names.str.contains(bad, regex=False).any()

def test_builder_can_return_750_unique_symbols_offline(monkeypatch):
    monkeypatch.setattr(universe_builder, "_read_html_tables", lambda url: (_ for _ in ()).throw(RuntimeError("offline")))
    selected = universe_builder.build_scan_universe(max_tickers=750)
    assert len(selected) == 750
    assert len(selected) == len(set(selected))

def test_builder_excludes_quarantined_symbols(monkeypatch):
    monkeypatch.setattr(universe_builder, "fetch_sp500_tickers", lambda: ["AAA", "BBB"])
    selected = universe_builder.build_scan_universe(
        include_watchlist=False, include_global_liquid=False,
        include_nasdaq100=False, include_starter_large_universe=False,
        include_broad_us=False, excluded_tickers={"AAA"}, max_tickers=10
    )
    assert selected == ["BBB"]

def test_failure_registry_quarantines_after_three_failures(monkeypatch, tmp_path):
    monkeypatch.setattr(universe_health, "REGISTRY_PATH", tmp_path / "health.json")
    for _ in range(3):
        universe_health.update_universe_health(["BAD", "GOOD"], ["GOOD"], {"BAD": "No data"})
    assert "BAD" in universe_health.quarantined_tickers()
    assert "GOOD" not in universe_health.quarantined_tickers()

def test_success_resets_consecutive_failures(monkeypatch, tmp_path):
    monkeypatch.setattr(universe_health, "REGISTRY_PATH", tmp_path / "health.json")
    for _ in range(3):
        universe_health.update_universe_health(["AAA"], [], {"AAA": "No data"})
    assert "AAA" in universe_health.quarantined_tickers()
    universe_health.update_universe_health(["AAA"], ["AAA"], {})
    assert "AAA" not in universe_health.quarantined_tickers()
