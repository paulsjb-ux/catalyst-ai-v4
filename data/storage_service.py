from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import json
import math
import os
import tempfile
from typing import Any

import pandas as pd

from data.cloud_store import (
    cloud_enabled,
    get_json as cloud_get_json,
    put_json as cloud_put_json,
)


LOCAL_KV_DIR = Path("storage/kv")
_STORAGE_STATUS: dict[str, Any] = {
    "backend": "local",
    "degraded": False,
    "last_error": "",
    "updated_at": "",
}


def _local_path(key: str) -> Path:
    safe = key.replace(":", "__").replace("/", "_")
    return LOCAL_KV_DIR / f"{safe}.json"


def _json_safe(value: Any) -> Any:
    """Convert common pandas/numpy/datetime values to strict JSON values."""
    if value is None:
        return None

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()

    # numpy scalar support without importing numpy directly.
    if hasattr(value, "item") and callable(value.item):
        try:
            return _json_safe(value.item())
        except Exception:
            pass

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    if pd.isna(value):
        return None

    return value


def local_put_json(key: str, value: Any) -> None:
    """Write a local fallback atomically so a crash cannot corrupt the file."""
    LOCAL_KV_DIR.mkdir(parents=True, exist_ok=True)
    destination = _local_path(key)
    payload = json.dumps(_json_safe(value), indent=2, allow_nan=False)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.stem}.", suffix=".tmp", dir=str(LOCAL_KV_DIR)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temp_name).replace(destination)
    finally:
        temp_path = Path(temp_name)
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def local_get_json(key: str, default: Any = None) -> Any:
    path = _local_path(key)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _set_status(backend: str, degraded: bool = False, error: str = "") -> None:
    _STORAGE_STATUS.update(
        {
            "backend": backend,
            "degraded": degraded,
            "last_error": error,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def storage_status() -> dict[str, Any]:
    return dict(_STORAGE_STATUS)


def put(key: str, value: Any) -> str:
    """Write locally first, then mirror to Supabase when configured.

    Local-first writes guarantee that the app never loses a user action because
    the network is unavailable. The previous implementation accidentally
    shadowed the imported cloud ``put_json`` function with a compatibility alias,
    which caused recursive calls instead of a cloud write. Explicit cloud aliases
    prevent that class of bug.
    """
    safe_value = _json_safe(value)
    local_put_json(key, safe_value)

    if not cloud_enabled():
        _set_status("local")
        return "local"

    try:
        cloud_put_json(key, safe_value)
        _set_status("Supabase + local")
        return "cloud+local"
    except Exception as exc:
        _set_status("local fallback", True, str(exc))
        return "local-fallback"


def get(key: str, default: Any = None) -> Any:
    """Prefer Supabase; use the local mirror when absent or unavailable."""
    if not cloud_enabled():
        _set_status("local")
        return local_get_json(key, default)

    try:
        cloud_value = cloud_get_json(key, None)
        if cloud_value is not None:
            local_put_json(key, cloud_value)
            _set_status("Supabase + local")
            return cloud_value

        # A missing key is not a failed Supabase connection.
        _set_status("Supabase + local")
        return local_get_json(key, default)
    except Exception as exc:
        _set_status("local fallback", True, str(exc))
        return local_get_json(key, default)


def dataframe_to_records(frame: pd.DataFrame) -> list[dict]:
    if frame is None or frame.empty:
        return []
    return [_json_safe(row) for row in frame.to_dict(orient="records")]


def records_to_dataframe(
    records: list[dict] | None, columns: list[str] | None = None
) -> pd.DataFrame:
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
