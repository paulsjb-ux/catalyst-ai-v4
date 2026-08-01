from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
import json, os, tempfile
from logging_config import configure_logging

LOGGER = configure_logging()
REGISTRY_PATH = Path("storage/universe_health.json")
QUARANTINE_FAILURES = 3
QUARANTINE_DAYS = 7

def _load() -> dict:
    try:
        value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Universe health registry could not be read: %s", exc)
        return {}

def _save(value: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=REGISTRY_PATH.parent, delete=False) as h:
        json.dump(value, h, indent=2, sort_keys=True)
        h.flush(); os.fsync(h.fileno()); temp_name = h.name
    os.replace(temp_name, REGISTRY_PATH)

def quarantined_tickers(failure_threshold: int = QUARANTINE_FAILURES, quarantine_days: int = QUARANTINE_DAYS) -> set[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=quarantine_days)
    output = set()
    for ticker, item in _load().items():
        if not isinstance(item, dict):
            continue
        try:
            when = datetime.fromisoformat(str(item.get("last_failure")))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        if int(item.get("consecutive_failures", 0) or 0) >= failure_threshold and when >= cutoff:
            output.add(str(ticker).upper())
    return output

def update_universe_health(requested: Iterable[str], loaded: Iterable[str], errors: dict[str, str]) -> dict:
    registry = _load()
    now = datetime.now(timezone.utc).isoformat()
    requested_set = {str(x).upper() for x in requested}
    loaded_set = {str(x).upper() for x in loaded}
    for ticker in requested_set:
        item = registry.get(ticker)
        item = item if isinstance(item, dict) else {}
        if ticker in loaded_set:
            item["consecutive_failures"] = 0
            item["success_count"] = int(item.get("success_count", 0) or 0) + 1
            item["last_success"] = now
            item.pop("last_error", None)
        else:
            item["consecutive_failures"] = int(item.get("consecutive_failures", 0) or 0) + 1
            item["failure_count"] = int(item.get("failure_count", 0) or 0) + 1
            item["last_failure"] = now
            item["last_error"] = str(errors.get(ticker, "No usable market data"))
        registry[ticker] = item
    _save(registry)
    q = quarantined_tickers()
    loaded_count = len(requested_set & loaded_set)
    return {
        "requested": len(requested_set),
        "loaded": loaded_count,
        "errors": len(requested_set) - loaded_count,
        "success_rate_pct": round(100 * loaded_count / max(1, len(requested_set)), 2),
        "quarantined": len(q),
        "quarantined_tickers": sorted(q),
    }

def reset_universe_health() -> None:
    REGISTRY_PATH.unlink(missing_ok=True)
