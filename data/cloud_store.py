from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
from typing import Any
from urllib import error, parse, request


TABLE_NAME = "catalyst_store"
LOCAL_BACKUP_DIR = Path("storage/backups")
_READ_CACHE_TTL_SECONDS = 30.0
_HEALTH_CACHE_TTL_SECONDS = 60.0
_CACHE_LOCK = threading.RLock()
_READ_CACHE: dict[str, tuple[float, Any]] = {}
_HEALTH_CACHE: tuple[float, dict[str, Any]] | None = None


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
    """Build headers for modern Supabase API keys and legacy JWT keys."""
    config = get_storage_config()
    headers = {
        "apikey": config.key,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Catalyst-AI/8.1-phase1",
    }

    # New sb_publishable_/sb_secret_ keys are API keys, not access-token JWTs.
    if config.key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {config.key}"

    if prefer:
        headers["Prefer"] = prefer
    return headers


def _encode_payload(payload: Any) -> bytes | None:
    if payload is None:
        return None
    return json.dumps(payload, allow_nan=False, separators=(",", ":")).encode("utf-8")


def _friendly_http_error(code: int, raw: str) -> RuntimeError:
    detail = raw.strip() or "No response body"
    lower = detail.lower()

    if code == 401:
        return RuntimeError(
            "Supabase rejected the API key (HTTP 401). Check that SUPABASE_URL "
            "and SUPABASE_KEY belong to the same project and contain no extra spaces. "
            f"Response: {detail}"
        )
    if code == 403:
        return RuntimeError(
            "Supabase permissions blocked the request (HTTP 403). Run the supplied "
            "supabase_setup.sql and check Row Level Security policies. "
            f"Response: {detail}"
        )
    if code == 404 or "pgrst205" in lower or "could not find the table" in lower:
        return RuntimeError(
            f"Supabase table '{TABLE_NAME}' is unavailable. Run docs/supabase_setup.sql. "
            f"Response: {detail}"
        )
    return RuntimeError(f"Cloud storage HTTP {code}: {detail}")


def _request(
    method: str,
    url: str,
    payload: Any | None = None,
    prefer: str | None = None,
    timeout: int = 12,
    retries: int = 3,
) -> tuple[int, Any]:
    body = _encode_payload(payload)
    last_error: Exception | None = None

    for attempt in range(max(1, retries)):
        req = request.Request(
            url=url,
            data=body,
            headers=_headers(prefer),
            method=method,
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw) if raw else None
                return response.status, parsed
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            last_error = _friendly_http_error(exc.code, raw)
            if exc.code < 500 and exc.code != 429:
                raise last_error from exc
        except error.URLError as exc:
            last_error = RuntimeError(f"Cloud storage connection failed: {exc.reason}")
        except TimeoutError as exc:
            last_error = RuntimeError("Cloud storage request timed out")

        if attempt < retries - 1:
            time.sleep(0.35 * (2**attempt))

    raise last_error or RuntimeError("Cloud storage request failed")


def _cache_get(key: str) -> tuple[bool, Any]:
    with _CACHE_LOCK:
        cached = _READ_CACHE.get(key)
        if not cached:
            return False, None
        expires_at, value = cached
        if time.monotonic() >= expires_at:
            _READ_CACHE.pop(key, None)
            return False, None
        return True, value


def _cache_put(key: str, value: Any) -> None:
    with _CACHE_LOCK:
        _READ_CACHE[key] = (time.monotonic() + _READ_CACHE_TTL_SECONDS, value)


def clear_cache(key: str | None = None) -> None:
    global _HEALTH_CACHE
    with _CACHE_LOCK:
        if key is None:
            _READ_CACHE.clear()
            _HEALTH_CACHE = None
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
    _request(
        "POST",
        _endpoint() + "?on_conflict=key",
        payload=row,
        prefer="resolution=merge-duplicates,return=minimal",
    )
    _cache_put(key, value)


def get_json(key: str, default: Any = None, *, use_cache: bool = True) -> Any:
    if not cloud_enabled():
        return default

    if use_cache:
        found, cached = _cache_get(key)
        if found:
            return cached

    url = _endpoint(key) + "&select=value&limit=1"
    _, rows = _request("GET", url)
    if not rows:
        return default

    value = rows[0].get("value", default)
    _cache_put(key, value)
    return value


def delete_key(key: str) -> None:
    if not cloud_enabled():
        raise RuntimeError("Cloud storage is not configured.")
    _request("DELETE", _endpoint(key), prefer="return=minimal")
    clear_cache(key)


def list_keys(prefix: str | None = None) -> list[str]:
    if not cloud_enabled():
        return []

    url = _endpoint() + "?select=key&order=key.asc"
    if prefix:
        url += f"&key=like.{parse.quote(prefix + '%', safe='')}"
    _, rows = _request("GET", url)
    return [str(row.get("key")) for row in (rows or []) if row.get("key")]


def health_check(*, force: bool = False) -> dict[str, Any]:
    global _HEALTH_CACHE

    config = get_storage_config()
    result: dict[str, Any] = {
        "configured": config.enabled,
        "reachable": False,
        "table_ready": False,
        "read_ready": False,
        "write_ready": False,
        "backend": "Supabase" if config.enabled else "Local fallback",
        "error": None,
    }

    if not config.enabled:
        return result

    with _CACHE_LOCK:
        if not force and _HEALTH_CACHE and time.monotonic() < _HEALTH_CACHE[0]:
            return dict(_HEALTH_CACHE[1])

    probe_key = "__catalyst_healthcheck__"
    try:
        # Read proves URL, API key, PostgREST and table visibility.
        url = _endpoint() + "?select=key&limit=1"
        _request("GET", url)
        result["reachable"] = True
        result["table_ready"] = True
        result["read_ready"] = True

        # A reversible write/read/delete probe catches RLS issues up front.
        probe_value = {"checked_at": datetime.now(timezone.utc).isoformat()}
        put_json(probe_key, probe_value)
        stored = get_json(probe_key, None, use_cache=False)
        if stored != probe_value:
            raise RuntimeError("Supabase health probe was written but could not be read back.")
        delete_key(probe_key)
        result["write_ready"] = True
    except Exception as exc:
        result["error"] = str(exc)
        try:
            clear_cache(probe_key)
        except Exception:
            pass

    with _CACHE_LOCK:
        _HEALTH_CACHE = (
            time.monotonic() + _HEALTH_CACHE_TTL_SECONDS,
            dict(result),
        )
    return result


def create_backup_payload(
    watchlist: list[dict],
    scan_index: list[dict],
    scans: dict[str, list[dict]],
) -> dict:
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
    put_json(key, payload)
    put_json("backup:latest", {"key": key, "created_at": payload.get("created_at")})
    return key


def save_local_backup(payload: dict) -> Path:
    LOCAL_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = LOCAL_BACKUP_DIR / f"catalyst_backup_{timestamp}.json"
    path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    return path


def load_cloud_backup(key: str = "backup:latest") -> dict | None:
    pointer = get_json(key)
    if not pointer:
        return None

    if key == "backup:latest" and isinstance(pointer, dict) and pointer.get("key"):
        return get_json(str(pointer["key"]))

    return pointer
