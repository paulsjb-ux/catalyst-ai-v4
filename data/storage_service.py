from __future__ import annotations

from datetime import date, datetime, timezone
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
import pandas as pd

from data.cloud_store import cloud_enabled, get_json as cloud_get_json, put_json as cloud_put_json


LOCAL_KV_DIR = Path("storage/kv")
_STORAGE_STATUS: dict[str, Any] = {"backend": "local", "degraded": False, "last_error": "", "updated_at": ""}


def _local_path(key: str) -> Path:
    safe = key.replace(":", "__").replace("/", "_")
    return LOCAL_KV_DIR / f"{safe}.json"


def _json_default(value: Any) -> Any:
    if value is pd.NA:
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _normalise_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if value is pd.NA:
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return _normalise_json(value.item())
    if isinstance(value, np.ndarray):
        return [_normalise_json(item) for item in value.tolist()]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _normalise_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalise_json(item) for item in value]
    return _json_default(value)


def _json_dumps(value: Any, *, indent: int | None = None) -> str:
    return json.dumps(_normalise_json(value), allow_nan=False, indent=indent)


def local_put_json(key: str, value: Any) -> None:
    """Atomically write local fallback data to avoid partial/corrupt JSON."""
    LOCAL_KV_DIR.mkdir(parents=True, exist_ok=True)
    destination = _local_path(key)
    content = _json_dumps(value, indent=2)
    fd, temp_name = tempfile.mkstemp(prefix=destination.name, suffix=".tmp", dir=str(LOCAL_KV_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def local_get_json(key: str, default: Any = None) -> Any:
    path = _local_path(key)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
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
    """Write locally first, then cloud; local persistence is always retained."""
    local_put_json(key, value)
    if cloud_enabled():
        try:
            cloud_put_json(key, value)
            _set_status("cloud+local")
            return "cloud+local"
        except Exception as exc:
            _set_status("local fallback", True, str(exc))
            return "local-fallback"
    _set_status("local")
    return "local"


def get(key: str, default: Any = None) -> Any:
    """Prefer cloud data and preserve accurate status when a cloud key is absent."""
    if cloud_enabled():
        try:
            sentinel = object()
            cloud_value = cloud_get_json(key, sentinel)
            if cloud_value is not sentinel:
                local_put_json(key, cloud_value)
                _set_status("cloud+local")
                return cloud_value
            _set_status("cloud+local")
            return local_get_json(key, default)
        except Exception as exc:
            _set_status("local fallback", True, str(exc))
            return local_get_json(key, default)
    _set_status("local")
    return local_get_json(key, default)


def dataframe_to_records(frame: pd.DataFrame) -> list[dict]:
    if frame is None or frame.empty:
        return []
    records = frame.to_dict(orient="records")
    cleaned: list[dict] = []
    for row in records:
        output: dict[str, Any] = {}
        for key, value in row.items():
            try:
                missing = bool(pd.isna(value))
            except (TypeError, ValueError):
                missing = False
            output[key] = None if missing else _json_default(value) if isinstance(value, (np.generic, pd.Timestamp, datetime, date, Path, set, np.ndarray)) else value
        cleaned.append(output)
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


# Backwards-compatible aliases used throughout the app.
def put_json(key: str, value: Any) -> str:
    return put(key, value)


def get_json(key: str, default: Any = None) -> Any:
    return get(key, default)
