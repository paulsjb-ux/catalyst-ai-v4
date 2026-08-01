from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd

from data import cloud_store, daily_routine_store, history_store, market_data


def test_daily_routine_payload_round_trips_through_storage_service(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_routine_store, "STORE_DIR", tmp_path)
    monkeypatch.setattr(daily_routine_store, "SCAN_PATH", tmp_path / "latest_scan.csv")
    monkeypatch.setattr(daily_routine_store, "PLANS_PATH", tmp_path / "latest_plans.csv")
    monkeypatch.setattr(daily_routine_store, "REGIME_PATH", tmp_path / "latest_regime.json")
    monkeypatch.setattr(daily_routine_store, "SUMMARY_PATH", tmp_path / "latest_summary.json")

    saved = {}
    monkeypatch.setattr(
        daily_routine_store,
        "put",
        lambda key, value: saved.update({key: value}) or "cloud+local",
    )
    monkeypatch.setattr(
        daily_routine_store,
        "get",
        lambda key, default=None: saved.get(key, default),
    )

    daily_routine_store.save_latest_routine(
        scan=pd.DataFrame([{"ticker": "AAA", "score": 80}]),
        plans=pd.DataFrame([{"ticker": "AAA", "entry_price": 10.0}]),
        regime={"regime": "RISK_ON"},
        summary={"success": True},
    )

    # Remove conventional local files to simulate a fresh Streamlit instance.
    for path in tmp_path.iterdir():
        path.unlink()

    restored = daily_routine_store.load_latest_routine()
    assert restored["scan"].iloc[0]["ticker"] == "AAA"
    assert restored["plans"].iloc[0]["entry_price"] == 10.0
    assert restored["regime"]["regime"] == "RISK_ON"
    assert (tmp_path / "latest_scan.csv").exists()


def test_scan_ids_are_collision_resistant():
    now = datetime(2026, 8, 1, 8, 0, 0, tzinfo=timezone.utc)
    first = history_store._new_scan_id(now)
    second = history_store._new_scan_id(now)
    assert first != second
    assert first.startswith("20260801_080000_000000_")


def test_market_memory_cache_uses_requested_ttl(monkeypatch, tmp_path):
    monkeypatch.setattr(market_data, "CACHE_DIR", tmp_path)
    market_data._MEMORY_CACHE.clear()
    frame = pd.DataFrame({"Close": range(80)})
    before = market_data.time.monotonic()
    market_data._write_cache("AAA", "1y", "1d", frame, datetime.now(timezone.utc), 3)
    expires_at, _ = market_data._MEMORY_CACHE[("AAA", "1y", "1d")]
    assert 170 <= expires_at - before <= 190


def test_publishable_key_preferred_and_conflict_reported(monkeypatch):
    values = {
        "SUPABASE_URL": "https://abc.supabase.co",
        "SUPABASE_KEY": "sb_publishable_normal",
        "SUPABASE_SECRET_KEY": "sb_secret_admin",
    }
    monkeypatch.setattr(cloud_store, "_secret", lambda name, default="": values.get(name, default))
    config = cloud_store.get_storage_config()
    assert config.key == "sb_publishable_normal"
    assert config.key_type == "publishable"
    assert set(config.configured_key_sources) == {"SUPABASE_KEY", "SUPABASE_SECRET_KEY"}
    assert "Multiple Supabase keys" in config.warning
