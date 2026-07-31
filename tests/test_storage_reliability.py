from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from data import cloud_store, storage_service


def test_modern_supabase_key_uses_apikey_only(monkeypatch):
    monkeypatch.setattr(cloud_store, "get_storage_config", lambda: cloud_store.StorageConfig("https://example.supabase.co", "sb_publishable_test", True))
    headers = cloud_store._headers()
    assert headers["apikey"] == "sb_publishable_test"
    assert "Authorization" not in headers


def test_legacy_jwt_key_keeps_authorization(monkeypatch):
    monkeypatch.setattr(cloud_store, "get_storage_config", lambda: cloud_store.StorageConfig("https://example.supabase.co", "eyJlegacy", True))
    headers = cloud_store._headers()
    assert headers["Authorization"] == "Bearer eyJlegacy"


def test_local_storage_serializes_common_dataframe_values(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_service, "LOCAL_KV_DIR", tmp_path)
    payload = {
        "integer": np.int64(7),
        "number": np.float64(1.5),
        "missing": np.nan,
        "timestamp": pd.Timestamp("2026-07-31T12:00:00Z"),
        "path": Path("example/file.csv"),
    }
    storage_service.local_put_json("sample", payload)
    restored = storage_service.local_get_json("sample")
    assert restored["integer"] == 7
    assert restored["number"] == 1.5
    assert restored["missing"] is None
    assert restored["timestamp"].startswith("2026-07-31")
    assert restored["path"] == "example/file.csv"


def test_missing_cloud_key_keeps_cloud_status(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "LOCAL_KV_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "cloud_enabled", lambda: True)
    monkeypatch.setattr(storage_service, "cloud_get_json", lambda key, default=None: default)
    storage_service.local_put_json("missing", {"local": True})
    assert storage_service.get("missing") == {"local": True}
    assert storage_service.storage_status()["backend"] == "cloud+local"
    assert storage_service.storage_status()["degraded"] is False


def test_cloud_read_cache_avoids_duplicate_request(monkeypatch):
    cloud_store.clear_read_cache()
    monkeypatch.setattr(cloud_store, "cloud_enabled", lambda: True)
    monkeypatch.setattr(cloud_store, "_endpoint", lambda key=None: "https://example.test")
    calls = []
    def fake_request(*args, **kwargs):
        calls.append(1)
        return 200, [{"value": {"ok": True}}]
    monkeypatch.setattr(cloud_store, "_request", fake_request)
    assert cloud_store.get_json("cache-key") == {"ok": True}
    assert cloud_store.get_json("cache-key") == {"ok": True}
    assert len(calls) == 1
