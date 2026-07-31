from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import threading
import time
from typing import Any
from urllib import error, parse, request

try:
    import numpy as np
except Exception:  # pragma: no cover - optional at import time
    np = None
try:
    import pandas as pd
except Exception:  # pragma: no cover - optional at import time
    pd = None


TABLE_NAME = "catalyst_store"
LOCAL_BACKUP_DIR = Path("storage/backups")
READ_CACHE_TTL_SECONDS = 45
_CACHE_LOCK = threading.RLock()
_READ_CACHE: dict[str, tuple[float, Any]] = {}


@dataclass(frozen=True)
class StorageConfig:
    url: str
    key: str
    enabled: bool


def _secret(name: str, default: str = "") -> str:
    """Read from Streamlit secrets when available, then environment variables."""
    try:
        import streamlit as st
        value = st.secrets.get(name, default)
        if value:
            return str(value).strip()
    except Exception:
        pass
    return str(os.getenv(name, default) or default).strip()


def get_storage_config() -> StorageConfig:
    url = _secret("SUPABASE_URL").rstrip("/")
    key = _secret("SUPABASE_KEY")
    return StorageConfig(url=url, key=key, enabled=bool(url and key))


def cloud_enabled() -> bool:
    return get_storage_config().enabled


def _endpoint(key: str | None = None) -> str:
    config = get_storage_config()
    base = f"{config.url}/rest/v1/{TABLE_NAME}"
    if key is None:
        return base
    return f"{base}?key=eq.{parse.quote(key, safe='')}"


def _headers(prefer: str | None = None) -> dict[str, str]:
    """Build PostgREST headers for modern and legacy Supabase keys.

    Modern ``sb_publishable_``/``sb_secret_`` values are API keys rather than
    user JWTs, so they are sent only as ``apikey``. Legacy JWT-shaped project
    keys retain the Bearer header for compatibility.
    """
    config = get_storage_config()
    headers = {
        "apikey": config.key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if config.key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {config.key}"
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _json_default(value: Any) -> Any:
    if pd is not None:
        if isinstance(value, (pd.Timestamp, datetime)):
            return value.isoformat()
        if value is pd.NA:
            return None
    if isinstance(value, datetime):
        return value.isoformat()
    if np is not None:
        if isinstance(value, np.generic):
            value = value.item()
            if isinstance(value, float) and not math.isfinite(value):
                return None
            return value
        elif isinstance(value, np.ndarray):
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
    if pd is not None and value is pd.NA:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if pd is not None and isinstance(value, pd.Timestamp):
        return value.isoformat()
    if np is not None and isinstance(value, np.generic):
        return _normalise_json(value.item())
    if np is not None and isinstance(value, np.ndarray):
        return [_normalise_json(item) for item in value.tolist()]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _normalise_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalise_json(item) for item in value]
    return _json_default(value)


def _json_dumps(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(_normalise_json(payload), allow_nan=False, indent=indent)


def _request(
    method: str,
    url: str,
    payload: Any | None = None,
    prefer: str | None = None,
    timeout: int = 12,
    retries: int = 3,
) -> tuple[int, Any]:
    body = None if payload is None else _json_dumps(payload).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(max(1, retries)):
        req = request.Request(url=url, data=body, headers=_headers(prefer), method=method)
        try:
            with request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw) if raw else None
                return response.status, parsed
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"Cloud storage HTTP {exc.code}: {raw}")
            if exc.code < 500 and exc.code != 429:
                raise last_error from exc
        except error.URLError as exc:
            last_error = RuntimeError(f"Cloud storage connection failed: {exc.reason}")
        except TimeoutError as exc:
            last_error = RuntimeError("Cloud storage request timed out")
        if attempt < retries - 1:
            time.sleep(0.35 * (2 ** attempt))
    raise last_error or RuntimeError("Cloud storage request failed")


def _cache_get(key: str) -> tuple[bool, Any]:
    now = time.monotonic()
    with _CACHE_LOCK:
        item = _READ_CACHE.get(key)
        if item is None:
            return False, None
        expires_at, value = item
        if now >= expires_at:
            _READ_CACHE.pop(key, None)
            return False, None
        return True, value


def _cache_set(key: str, value: Any) -> None:
    with _CACHE_LOCK:
        _READ_CACHE[key] = (time.monotonic() + READ_CACHE_TTL_SECONDS, value)


def clear_read_cache(key: str | None = None) -> None:
    with _CACHE_LOCK:
        if key is None:
            _READ_CACHE.clear()
        else:
            _READ_CACHE.pop(key, None)


def put_json(key: str, value: Any) -> None:
    if not cloud_enabled():
        raise RuntimeError("Cloud storage is not configured.")
    row = {
        "key": key,
        "value": value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _request("POST", _endpoint(), payload=row, prefer="resolution=merge-duplicates,return=minimal")
    _cache_set(key, value)


def put_many(items: dict[str, Any]) -> None:
    """Upsert multiple key/value records in one request."""
    if not items:
        return
    if not cloud_enabled():
        raise RuntimeError("Cloud storage is not configured.")
    updated_at = datetime.now(timezone.utc).isoformat()
    rows = [{"key": key, "value": value, "updated_at": updated_at} for key, value in items.items()]
    _request("POST", _endpoint(), payload=rows, prefer="resolution=merge-duplicates,return=minimal")
    for key, value in items.items():
        _cache_set(key, value)


def get_json(key: str, default: Any = None, *, use_cache: bool = True) -> Any:
    if not cloud_enabled():
        return default
    if use_cache:
        found, value = _cache_get(key)
        if found:
            return value
    url = _endpoint(key) + "&select=value"
    _, rows = _request("GET", url)
    value = default if not rows else rows[0].get("value", default)
    _cache_set(key, value)
    return value


def delete_key(key: str) -> None:
    if not cloud_enabled():
        raise RuntimeError("Cloud storage is not configured.")
    _request("DELETE", _endpoint(key), prefer="return=minimal")
    clear_read_cache(key)


def list_keys(prefix: str | None = None) -> list[str]:
    if not cloud_enabled():
        return []
    url = _endpoint() + "?select=key&order=key.asc"
    if prefix:
        url += f"&key=like.{parse.quote(prefix + '%', safe='')}"
    _, rows = _request("GET", url)
    return [str(row.get("key")) for row in (rows or []) if row.get("key")]


def health_check() -> dict:
    config = get_storage_config()
    result = {
        "configured": config.enabled,
        "reachable": False,
        "table_ready": False,
        "backend": "Supabase" if config.enabled else "Local fallback",
        "error": None,
    }
    if not config.enabled:
        return result
    try:
        url = _endpoint() + "?select=key&limit=1"
        _request("GET", url, retries=2)
        result["reachable"] = True
        result["table_ready"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result


def create_backup_payload(watchlist: list[dict], scan_index: list[dict], scans: dict[str, list[dict]]) -> dict:
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "watchlist": watchlist,
        "scan_index": scan_index,
        "scans": scans,
    }


def save_cloud_backup(payload: dict) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    key = f"backup:{timestamp}"
    put_many({
        key: payload,
        "backup:latest": {"key": key, "created_at": payload.get("created_at")},
    })
    return key


def save_local_backup(payload: dict) -> Path:
    LOCAL_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = LOCAL_BACKUP_DIR / f"catalyst_backup_{timestamp}.json"
    path.write_text(_json_dumps(payload, indent=2), encoding="utf-8")
    return path


def load_cloud_backup(key: str = "backup:latest") -> dict | None:
    pointer = get_json(key)
    if not pointer:
        return None
    if key == "backup:latest" and isinstance(pointer, dict) and pointer.get("key"):
        return get_json(str(pointer["key"]))
    return pointer
