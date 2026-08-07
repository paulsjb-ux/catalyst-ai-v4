from pathlib import Path
import json
import pandas as pd

from engine.auto_validation import (
    load_tracker,
    merge_tracker_evidence,
    record_daily_run,
    recover_validation_days,
    tracker_summary,
)


def test_no_trade_day_counts_once(tmp_path: Path):
    path = tmp_path / "tracker.json"
    empty = pd.DataFrame()
    first = record_daily_run(empty, empty, {"regime": "DEFENSIVE"}, run_at="2026-08-05T08:00:00+00:00", path=path)
    assert tracker_summary(first)["days_completed"] == 1
    second = record_daily_run(empty, empty, {"regime": "DEFENSIVE"}, run_at="2026-08-05T10:00:00+00:00", path=path)
    assert tracker_summary(second)["days_completed"] == 1
    assert second["days"][0]["verdict"] == "NO TRADE"


def test_manual_recovery_adds_unique_days_without_trades(tmp_path: Path):
    path = tmp_path / "tracker.json"
    recovered = recover_validation_days(["2026-08-05", "2026-08-06", "2026-08-06"], path=path)
    assert tracker_summary(recovered)["days_completed"] == 2
    assert recovered["trades"] == []
    assert all(day.get("recovered") for day in recovered["days"])


def test_import_merges_days_and_trades_by_unique_keys(tmp_path: Path):
    path = tmp_path / "tracker.json"
    recover_validation_days(["2026-08-05"], path=path)
    incoming = {
        "days": [
            {"date": "2026-08-05", "verdict": "TRADE"},
            {"date": "2026-08-06", "verdict": "NO TRADE"},
        ],
        "trades": [
            {"id": "2026-08-05-MSFT", "ticker": "MSFT", "status": "OPEN"},
        ],
    }
    merged = merge_tracker_evidence(incoming, path=path)
    assert tracker_summary(merged)["days_completed"] == 2
    assert len(merged["trades"]) == 1
    saved = json.loads(path.read_text())
    assert len(saved["days"]) == 2
