from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

STORE_DIR = Path("storage/daily_routine")
SCAN_PATH = STORE_DIR / "latest_scan.csv"
PLANS_PATH = STORE_DIR / "latest_trade_plans.csv"
REGIME_PATH = STORE_DIR / "latest_regime.json"
SUMMARY_PATH = STORE_DIR / "latest_summary.json"


def save_latest_routine(*, scan: pd.DataFrame, plans: pd.DataFrame, regime: dict, summary: dict) -> None:
    """Persist the latest complete daily-routine payload for use across Streamlit sessions."""
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    (scan if isinstance(scan, pd.DataFrame) else pd.DataFrame()).to_csv(SCAN_PATH, index=False)
    (plans if isinstance(plans, pd.DataFrame) else pd.DataFrame()).to_csv(PLANS_PATH, index=False)
    REGIME_PATH.write_text(json.dumps(regime or {}, indent=2, default=str), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary or {}, indent=2, default=str), encoding="utf-8")


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_latest_routine() -> dict:
    """Load the latest persisted routine payload, returning safe empty defaults."""
    return {
        "scan": _read_csv(SCAN_PATH),
        "plans": _read_csv(PLANS_PATH),
        "regime": _read_json(REGIME_PATH),
        "summary": _read_json(SUMMARY_PATH),
    }
