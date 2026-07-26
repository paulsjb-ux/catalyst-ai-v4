from __future__ import annotations

from pathlib import Path
import json
import math
import os
import tempfile

import pandas as pd

STORE_DIR = Path("storage/daily_routine")
SCAN_PATH = STORE_DIR / "latest_scan.csv"
PLANS_PATH = STORE_DIR / "latest_trade_plans.csv"
REGIME_PATH = STORE_DIR / "latest_regime.json"
SUMMARY_PATH = STORE_DIR / "latest_summary.json"


def _json_safe(value):
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
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        temp_name = handle.name
    os.replace(temp_name, path)


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
        frame.to_csv(handle, index=False)
        temp_name = handle.name
    os.replace(temp_name, path)


def save_latest_routine(*, scan: pd.DataFrame, plans: pd.DataFrame, regime: dict, summary: dict) -> None:
    """Atomically persist the complete Daily Routine payload across Streamlit sessions."""
    scan_frame = scan if isinstance(scan, pd.DataFrame) else pd.DataFrame()
    plan_frame = plans if isinstance(plans, pd.DataFrame) else pd.DataFrame()
    _atomic_csv(SCAN_PATH, scan_frame)
    _atomic_csv(PLANS_PATH, plan_frame)
    _atomic_text(REGIME_PATH, json.dumps(_json_safe(regime or {}), indent=2, ensure_ascii=False))
    _atomic_text(SUMMARY_PATH, json.dumps(_json_safe(summary or {}), indent=2, ensure_ascii=False))


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError, OSError):
        return pd.DataFrame()


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def load_latest_routine() -> dict:
    """Load the latest persisted routine payload, returning safe empty defaults."""
    return {
        "scan": _read_csv(SCAN_PATH),
        "plans": _read_csv(PLANS_PATH),
        "regime": _read_json(REGIME_PATH),
        "summary": _read_json(SUMMARY_PATH),
    }
