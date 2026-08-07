from pathlib import Path

from version import APP_VERSION
from engine import version as engine_version
from reports import version as reports_version
from engine.daily_routine import RoutineResult, _record


def test_version_is_single_source_of_truth():
    assert APP_VERSION == "14.4.0"
    assert engine_version.__version__ == APP_VERSION
    assert reports_version.APP_VERSION == APP_VERSION
    assert 'version = "14.4.0"' in Path("pyproject.toml").read_text(encoding="utf-8")


def test_stage_timings_are_exported_in_summary():
    result = RoutineResult(started_at="2026-08-07T00:00:00+00:00")
    _record(result, "Market data", "complete", "ok", 1.23456)
    summary = result.summary()
    assert summary["stages"][0]["duration_seconds"] == 1.235
    assert summary["stage_timings"]["Market data"] == 1.235


def test_theme_has_one_public_apply_theme():
    source = Path("ui/theme.py").read_text(encoding="utf-8")
    assert source.count("def apply_theme()") == 1
    assert "_apply_theme_v12" not in source
    assert "_apply_theme_v143" not in source


def test_expired_daily_cache_uses_short_incremental_refresh(monkeypatch):
    from datetime import datetime, timezone
    import pandas as pd
    from data import market_data

    dates = pd.date_range("2026-01-01", periods=80, freq="D")
    stale = pd.DataFrame({"Close": range(80), "Volume": range(80)}, index=dates)
    recent_dates = pd.date_range(dates[-7], periods=7, freq="D")
    recent = pd.DataFrame({"Close": range(73, 80), "Volume": range(73, 80)}, index=recent_dates)
    periods = []

    def fake_read(ticker, period, interval, max_age_minutes, allow_expired=False):
        return stale if allow_expired else None

    def fake_batch(tickers, period, interval):
        periods.append(period)
        return {ticker: recent for ticker in tickers}

    monkeypatch.setattr(market_data, "_read_cache", fake_read)
    monkeypatch.setattr(market_data, "_download_batch", fake_batch)
    monkeypatch.setattr(market_data, "_write_cache", lambda *a, **k: None)
    result = market_data.download_history(["AAA"], period="1y", use_cache=True)
    assert periods == ["7d"]
    assert len(result.prices["AAA"]) == 80
    assert result.incremental_updates == 1
