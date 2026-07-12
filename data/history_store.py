from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd

from data.storage_service import dataframe_to_records, get, put, records_to_dataframe


STORAGE_DIR = Path("storage")
SCAN_HISTORY_DIR = STORAGE_DIR / "scans"
INDEX_FILE = STORAGE_DIR / "scan_index.json"
SCAN_INDEX_KEY = "scan_index"


@dataclass(frozen=True)
class SavedScan:
    scan_id: str
    saved_at: str
    file_path: str
    row_count: int
    buy_count: int
    watch_count: int


def ensure_storage() -> None:
    SCAN_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_FILE.exists():
        INDEX_FILE.write_text("[]", encoding="utf-8")


def _load_local_index() -> list[dict]:
    ensure_storage()
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _load_index() -> list[dict]:
    cloud_or_cache = get(SCAN_INDEX_KEY, None)
    if isinstance(cloud_or_cache, list):
        return cloud_or_cache
    return _load_local_index()


def _save_index(index: list[dict]) -> None:
    ensure_storage()
    INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")
    put(SCAN_INDEX_KEY, index)


def save_scan(frame: pd.DataFrame) -> SavedScan | None:
    ensure_storage()
    if frame is None or frame.empty:
        return None

    saved_at_dt = datetime.now(timezone.utc)
    saved_at = saved_at_dt.isoformat()
    scan_id = saved_at_dt.strftime("%Y%m%d_%H%M%S")
    path = SCAN_HISTORY_DIR / f"scan_{scan_id}.csv"

    output = frame.copy()
    if "saved_at" not in output.columns:
        output.insert(0, "saved_at", saved_at)
    if "scan_id" not in output.columns:
        output.insert(0, "scan_id", scan_id)
    output.to_csv(path, index=False)

    buy_count = int((frame["signal"] == "BUY").sum()) if "signal" in frame.columns else 0
    watch_count = int((frame["signal"] == "WATCH").sum()) if "signal" in frame.columns else 0

    saved = SavedScan(
        scan_id=scan_id,
        saved_at=saved_at,
        file_path=str(path),
        row_count=len(frame),
        buy_count=buy_count,
        watch_count=watch_count,
    )

    put(f"scan:{scan_id}", dataframe_to_records(output))

    index = _load_index()
    index = [item for item in index if item.get("scan_id") != scan_id]
    index.append(saved.__dict__)
    index = sorted(index, key=lambda item: item.get("saved_at", ""))[-100:]
    _save_index(index)
    return saved


def list_saved_scans() -> pd.DataFrame:
    index = _load_index()
    columns = ["scan_id", "saved_at", "file_path", "row_count", "buy_count", "watch_count"]
    if not index:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(index).sort_values("saved_at", ascending=False).reset_index(drop=True)


def load_scan(scan_id: str) -> pd.DataFrame:
    records = get(f"scan:{scan_id}", None)
    if isinstance(records, list) and records:
        return records_to_dataframe(records)

    index = _load_index()
    match = next((item for item in index if item.get("scan_id") == scan_id), None)
    if not match:
        return pd.DataFrame()

    path = Path(match.get("file_path", ""))
    if not path.exists():
        return pd.DataFrame()

    frame = pd.read_csv(path)
    put(f"scan:{scan_id}", dataframe_to_records(frame))
    return frame


def load_latest_scan() -> pd.DataFrame:
    scans = list_saved_scans()
    if scans.empty:
        return pd.DataFrame()
    return load_scan(str(scans.iloc[0]["scan_id"]))


def load_previous_scan(current_scan_id: str | None = None) -> pd.DataFrame:
    scans = list_saved_scans()
    if scans.empty:
        return pd.DataFrame()

    if current_scan_id is None:
        return load_scan(str(scans.iloc[1]["scan_id"])) if len(scans) > 1 else pd.DataFrame()

    filtered = scans[scans["scan_id"] != current_scan_id]
    if filtered.empty:
        return pd.DataFrame()
    return load_scan(str(filtered.iloc[0]["scan_id"]))


def compare_scans(current: pd.DataFrame, previous: pd.DataFrame) -> pd.DataFrame:
    if current is None or current.empty or previous is None or previous.empty:
        return pd.DataFrame()

    wanted = ["ticker", "signal", "score", "close", "change_20d_pct"]
    current_trim = current[[col for col in wanted if col in current.columns]].copy()
    previous_trim = previous[[col for col in wanted if col in previous.columns]].copy()

    merged = current_trim.merge(previous_trim, on="ticker", how="left", suffixes=("_now", "_prev"))

    if "score_now" in merged.columns and "score_prev" in merged.columns:
        merged["score_change"] = merged["score_now"] - merged["score_prev"]

    if "signal_now" in merged.columns and "signal_prev" in merged.columns:
        merged["signal_change"] = merged.apply(
            lambda row: "NEW" if pd.isna(row["signal_prev"]) else (
                "UNCHANGED" if row["signal_now"] == row["signal_prev"] else f'{row["signal_prev"]} → {row["signal_now"]}'
            ),
            axis=1,
        )
    return merged
