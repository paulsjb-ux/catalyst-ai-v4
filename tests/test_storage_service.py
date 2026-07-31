import pandas as pd

from data.storage_service import dataframe_to_records, records_to_dataframe


def test_dataframe_record_round_trip():
    frame = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "score": [80, None],
        }
    )

    records = dataframe_to_records(frame)
    restored = records_to_dataframe(records)

    assert restored["ticker"].tolist() == ["AAPL", "MSFT"]
    assert records[1]["score"] is None


def test_cloud_calls_use_explicit_aliases_without_recursion(monkeypatch, tmp_path):
    from data import storage_service

    monkeypatch.setattr(storage_service, "LOCAL_KV_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "cloud_enabled", lambda: True)
    calls = []
    monkeypatch.setattr(storage_service, "cloud_put_json", lambda key, value: calls.append((key, value)))
    monkeypatch.setattr(storage_service, "cloud_get_json", lambda key, default=None: {"ok": True})

    assert storage_service.put("sample", {"value": 1}) == "cloud+local"
    assert storage_service.get("sample") == {"ok": True}
    assert calls == [("sample", {"value": 1})]


def test_local_write_serializes_numpy_datetime_and_nan(monkeypatch, tmp_path):
    from datetime import datetime
    import json
    import numpy as np
    from data import storage_service

    monkeypatch.setattr(storage_service, "LOCAL_KV_DIR", tmp_path)
    storage_service.local_put_json(
        "types",
        {
            "integer": np.int64(7),
            "decimal": np.float64(2.5),
            "missing": float("nan"),
            "when": datetime(2026, 7, 31, 12, 0),
        },
    )
    payload = json.loads((tmp_path / "types.json").read_text())
    assert payload["integer"] == 7
    assert payload["decimal"] == 2.5
    assert payload["missing"] is None
    assert payload["when"].startswith("2026-07-31T12:00:00")


def test_missing_cloud_key_keeps_cloud_status(monkeypatch, tmp_path):
    from data import storage_service

    monkeypatch.setattr(storage_service, "LOCAL_KV_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "cloud_enabled", lambda: True)
    monkeypatch.setattr(storage_service, "cloud_get_json", lambda key, default=None: None)
    storage_service.local_put_json("missing", {"local": True})

    assert storage_service.get("missing") == {"local": True}
    assert storage_service.storage_status()["backend"] == "Supabase + local"
    assert storage_service.storage_status()["degraded"] is False
