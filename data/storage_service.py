from __future__ import annotations

from pathlib import Path
import json
from typing import Any
from datetime import datetime, timezone

import pandas as pd

from data.cloud_store import cloud_enabled, get_json, put_json


LOCAL_KV_DIR = Path("storage/kv")
_STORAGE_STATUS: dict[str, Any] = {"backend": "local", "degraded": False, "last_error": "", "updated_at": ""}


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


def _set_status(backend: str, degraded: bool = False, error: str = "") -> None:
    _STORAGE_STATUS.update({
        "backend": backend,
        "degraded": degraded,
        "last_error": error,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })


def storage_status() -> dict[str, Any]:
    return dict(_STORAGE_STATUS)


def put(key: str, value: Any) -> str:
    """Write locally first; use cloud when configured and expose degraded state."""
    local_put_json(key, value)
    if cloud_enabled():
        try:
            put_json(key, value)
            _set_status("cloud+local")
            return "cloud+local"
        except Exception as exc:
            _set_status("local fallback", True, str(exc))
            return "local-fallback"
    _set_status("local")
    return "local"


def get(key: str, default: Any = None) -> Any:
    """Prefer cloud data; fall back to local cache."""
    if cloud_enabled():
        try:
            cloud_value = get_json(key, None)
            if cloud_value is not None:
                local_put_json(key, cloud_value)
                return cloud_value
        except Exception as exc:
            _set_status("local fallback", True, str(exc))
            return local_get_json(key, default)
    _set_status("local")
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


# Backwards-compatible aliases used by the alert health subsystem.
def put_json(key: str, value: Any) -> str:
    return put(key, value)


def get_json(key: str, default: Any = None) -> Any:
    return get(key, default)
