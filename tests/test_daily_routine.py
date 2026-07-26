from pathlib import Path
import pandas as pd

from engine.daily_routine import RoutineResult, _write_exports


def test_routine_summary_counts_signals():
    result = RoutineResult(started_at="2026-07-23T10:00:00+00:00")
    result.success = True
    result.scan_results = pd.DataFrame({"ticker": ["AAA", "BBB", "CCC"], "signal": ["BUY", "WATCH", "IGNORE"]})
    result.trade_plans = pd.DataFrame({"ticker": ["AAA"]})
    result.market_errors = {"BAD": "no data"}
    result.alert_result = {"generated": 2}
    result.exports = ["a.csv", "b.json"]
    summary = result.summary()
    assert summary["symbols_scanned"] == 3
    assert summary["buy_count"] == 1
    assert summary["watch_count"] == 1
    assert summary["trade_plan_count"] == 1
    assert summary["data_error_count"] == 1
    assert summary["alerts_generated"] == 2
    assert summary["exports_created"] == 2


def test_write_exports_creates_operational_files(tmp_path: Path):
    result = RoutineResult(started_at="2026-07-23T10:00:00+00:00")
    result.scan_results = pd.DataFrame({"ticker": ["AAA"], "signal": ["BUY"]})
    result.trade_plans = pd.DataFrame({"ticker": ["AAA"], "target_price": [12.0]})
    result.brief = {
        "generated_at": "2026-07-23T10:01:00+00:00",
        "regime": {},
        "priorities": [],
        "top_buys": pd.DataFrame(),
        "repeat_winners": pd.DataFrame(),
        "portfolio_alerts": pd.DataFrame(),
        "near_target": pd.DataFrame(),
        "near_stop": pd.DataFrame(),
        "signal_changes": pd.DataFrame(),
        "validation_updates": pd.DataFrame(),
    }
    paths = _write_exports(result, tmp_path)
    assert len(paths) == 4
    assert all(Path(path).exists() for path in paths)
    assert any(path.endswith(".md") for path in paths)
    assert any(path.endswith(".json") for path in paths)
