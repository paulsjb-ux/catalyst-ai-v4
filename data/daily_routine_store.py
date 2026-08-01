from __future__ import annotations

from pathlib import Path
import json
import math
import os
import tempfile
from typing import Any

import pandas as pd

from data.storage_service import dataframe_to_records, get, put, records_to_dataframe
from logging_config import configure_logging

LOGGER = configure_logging()
STORE_DIR = Path("storage/daily_routine")
SCAN_PATH = STORE_DIR / "latest_scan.csv"
PLANS_PATH = STORE_DIR / "latest_trade_plans.csv"
REGIME_PATH = STORE_DIR / "latest_regime.json"
SUMMARY_PATH = STORE_DIR / "latest_summary.json"
LATEST_ROUTINE_KEY = "daily_routine:latest"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    os.replace(temp_name, path)


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        delete=False,
    ) as handle:
        frame.to_csv(handle, index=False)
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    os.replace(temp_name, path)


def _payload(
    scan: pd.DataFrame,
    plans: pd.DataFrame,
    regime: dict,
    summary: dict,
) -> dict[str, Any]:
    return {
        "scan": dataframe_to_records(scan),
        "plans": dataframe_to_records(plans),
        "regime": _json_safe(regime or {}),
        "summary": _json_safe(summary or {}),
    }


def _write_local(payload: dict[str, Any]) -> None:
    _atomic_csv(SCAN_PATH, records_to_dataframe(payload.get("scan")))
    _atomic_csv(PLANS_PATH, records_to_dataframe(payload.get("plans")))
    _atomic_text(
        REGIME_PATH,
        json.dumps(payload.get("regime") or {}, indent=2, ensure_ascii=False),
    )
    _atomic_text(
        SUMMARY_PATH,
        json.dumps(payload.get("summary") or {}, indent=2, ensure_ascii=False),
    )


def save_latest_routine(
    *,
    scan: pd.DataFrame,
    plans: pd.DataFrame,
    regime: dict,
    summary: dict,
) -> None:
    """Persist the complete routine payload locally and through storage_service.

    storage_service always retains a local key/value copy and writes to Supabase
    when configured, so the latest Dashboard state survives Streamlit restarts.
    """
    scan_frame = scan if isinstance(scan, pd.DataFrame) else pd.DataFrame()
    plan_frame = plans if isinstance(plans, pd.DataFrame) else pd.DataFrame()
    payload = _payload(scan_frame, plan_frame, regime, summary)

    _write_local(payload)
    backend = put(LATEST_ROUTINE_KEY, payload)
    if backend == "local-fallback":
        LOGGER.warning(
            "Daily Routine payload saved locally because cloud persistence degraded."
        )


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        return pd.DataFrame()
    except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError) as exc:
        LOGGER.warning("Could not read Daily Routine CSV %s: %s", path, exc)
        return pd.DataFrame()


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        LOGGER.warning("Could not read Daily Routine JSON %s: %s", path, exc)
        return {}


def _local_payload() -> dict[str, Any]:
    return {
        "scan": dataframe_to_records(_read_csv(SCAN_PATH)),
        "plans": dataframe_to_records(_read_csv(PLANS_PATH)),
        "regime": _read_json(REGIME_PATH),
        "summary": _read_json(SUMMARY_PATH),
    }


def _normalise_payload(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    expected = {"scan", "plans", "regime", "summary"}
    if not expected.intersection(value):
        return None
    return {
        "scan": value.get("scan") if isinstance(value.get("scan"), list) else [],
        "plans": value.get("plans") if isinstance(value.get("plans"), list) else [],
        "regime": value.get("regime") if isinstance(value.get("regime"), dict) else {},
        "summary": value.get("summary") if isinstance(value.get("summary"), dict) else {},
    }


def load_latest_routine() -> dict:
    """Load cloud-backed latest routine data, with safe local recovery."""
    local_payload = _local_payload()
    stored = _normalise_payload(get(LATEST_ROUTINE_KEY, local_payload))
    payload = stored or local_payload

    # Rehydrate the conventional local files after a cloud restoration.
    try:
        _write_local(payload)
    except OSError as exc:
        LOGGER.warning("Could not refresh local Daily Routine files: %s", exc)

    return {
        "scan": records_to_dataframe(payload.get("scan")),
        "plans": records_to_dataframe(payload.get("plans")),
        "regime": payload.get("regime") or {},
        "summary": payload.get("summary") or {},
    }
