from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import pandas as pd

from data.cloud_store import cloud_enabled, get_json, put_json


LOCAL_KV_DIR = Path("storage/kv")


def _local_path(key: str) -> Path:
    safe = key.replace(":", "__").replace("/", "_")
    return LOCAL_KV_DIR / f"{safe}.json"


def local_put_json(key: str, value: Any) -> None:
    LOCAL_KV_DIR.mkdir(parents=True, exist_ok=True)
    _local_path(key).write_text(json.dumps(value, indent=2), encoding="utf-8")


def local_get_json(key: str, default: Any = None) -> Any:
    path = _local_path(key)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def put(key: str, value: Any) -> str:
    """Write to cloud when configured, always retaining a local fallback copy."""
    local_put_json(key, value)
    if cloud_enabled():
        put_json(key, value)
        return "cloud+local"
    return "local"


def get(key: str, default: Any = None) -> Any:
    """Prefer cloud data; fall back to local cache."""
    if cloud_enabled():
        try:
            cloud_value = get_json(key, None)
            if cloud_value is not None:
                local_put_json(key, cloud_value)
                return cloud_value
        except Exception:
            pass
    return local_get_json(key, default)


def dataframe_to_records(frame: pd.DataFrame) -> list[dict]:
    if frame is None or frame.empty:
        return []

    records = frame.to_dict(orient="records")
    cleaned = []

    for row in records:
        cleaned.append({
            key: (None if pd.isna(value) else value)
            for key, value in row.items()
        })

    return cleaned


def records_to_dataframe(records: list[dict] | None, columns: list[str] | None = None) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=columns or [])
    frame = pd.DataFrame(records)
    if columns:
        for column in columns:
            if column not in frame.columns:
                frame[column] = None
        frame = frame[columns]
    return frame
