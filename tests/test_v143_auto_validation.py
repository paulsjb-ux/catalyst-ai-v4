from pathlib import Path
import pandas as pd

from engine.auto_validation import record_daily_run, tracker_summary, load_tracker


def _desk():
    return pd.DataFrame([{
        "ticker": "MSFT", "swing_status": "PRIORITY", "entry_price": 100,
        "target_price": 110, "stop_loss": 95, "position_size_pct": 15, "score": 83,
    }])


def test_records_once_per_day_and_closes_target(tmp_path: Path):
    path = tmp_path / "tracker.json"
    scan = pd.DataFrame([{"ticker": "MSFT", "latest_price": 100}])
    first = record_daily_run(_desk(), scan, {"regime": "BULL"}, run_at="2026-08-03T09:00:00+00:00", path=path)
    assert len(first["days"]) == 1
    assert len(first["trades"]) == 1
    second = record_daily_run(_desk(), scan, {"regime": "BULL"}, run_at="2026-08-03T10:00:00+00:00", path=path)
    assert len(second["days"]) == 1
    target_scan = pd.DataFrame([{"ticker": "MSFT", "latest_price": 111}])
    final = record_daily_run(pd.DataFrame(), target_scan, {"regime": "BULL"}, run_at="2026-08-04T09:00:00+00:00", path=path)
    assert final["trades"][0]["status"] == "CLOSED"
    assert final["trades"][0]["exit_reason"] == "TARGET"
    assert tracker_summary(final)["closed_trades"] == 1


def test_load_missing_tracker_is_safe(tmp_path: Path):
    tracker = load_tracker(tmp_path / "missing.json")
    assert tracker["target_days"] == 30
    assert tracker_summary(tracker)["status"] == "COLLECTING"
