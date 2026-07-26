from pathlib import Path

import pandas as pd

from data import daily_routine_store as store


def test_save_and_load_latest_routine(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STORE_DIR", tmp_path)
    monkeypatch.setattr(store, "SCAN_PATH", tmp_path / "latest_scan.csv")
    monkeypatch.setattr(store, "PLANS_PATH", tmp_path / "latest_trade_plans.csv")
    monkeypatch.setattr(store, "REGIME_PATH", tmp_path / "latest_regime.json")
    monkeypatch.setattr(store, "SUMMARY_PATH", tmp_path / "latest_summary.json")

    scan = pd.DataFrame([{"ticker": "AAA", "signal": "WATCH", "score": 70}])
    plans = pd.DataFrame([{"ticker": "AAA", "entry_price": 10.0}])
    regime = {"regime": "DEFENSIVE", "market_score": 35}
    summary = {"success": True, "watch_count": 1}

    store.save_latest_routine(scan=scan, plans=plans, regime=regime, summary=summary)
    loaded = store.load_latest_routine()

    assert loaded["scan"].iloc[0]["ticker"] == "AAA"
    assert loaded["plans"].iloc[0]["entry_price"] == 10.0
    assert loaded["regime"]["regime"] == "DEFENSIVE"
    assert loaded["summary"]["watch_count"] == 1
