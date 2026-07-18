from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
from urllib import error, parse, request


TABLE_NAME = "catalyst_store"
LOCAL_BACKUP_DIR = Path("storage/backups")


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
            return str(value)
    except Exception:
        pass
    return str(os.getenv(name, default) or default)


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
    config = get_storage_config()
    headers = {
        "apikey": config.key,
        "Authorization": f"Bearer {config.key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _request(
    method: str,
    url: str,
    payload: Any | None = None,
    prefer: str | None = None,
    timeout: int = 12,
) -> tuple[int, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
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
        raise RuntimeError(f"Cloud storage HTTP {exc.code}: {raw}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Cloud storage connection failed: {exc.reason}") from exc


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
        _endpoint(),
        payload=row,
        prefer="resolution=merge-duplicates,return=minimal",
    )


def get_json(key: str, default: Any = None) -> Any:
    if not cloud_enabled():
        return default

    url = _endpoint(key) + "&select=value"
    _, rows = _request("GET", url)
    if not rows:
        return default
    return rows[0].get("value", default)


def delete_key(key: str) -> None:
    if not cloud_enabled():
        raise RuntimeError("Cloud storage is not configured.")
    _request("DELETE", _endpoint(key), prefer="return=minimal")


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
        _request("GET", url)
        result["reachable"] = True
        result["table_ready"] = True
    except Exception as exc:
        result["error"] = str(exc)

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
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_cloud_backup(key: str = "backup:latest") -> dict | None:
    pointer = get_json(key)
    if not pointer:
        return None

    if key == "backup:latest" and isinstance(pointer, dict) and pointer.get("key"):
        return get_json(str(pointer["key"]))

    return pointer
