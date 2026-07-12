from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

from data.cloud_store import (
    cloud_enabled,
    create_backup_payload,
    load_cloud_backup,
    save_cloud_backup,
    save_local_backup,
)
from data.history_store import SCAN_INDEX_KEY, list_saved_scans, load_scan
from data.storage_service import dataframe_to_records, put
from data.watchlist_store import WATCHLIST_KEY, load_watchlist, save_watchlist


def build_current_backup() -> dict:
    watchlist = dataframe_to_records(load_watchlist())
    scan_index_frame = list_saved_scans()
    scan_index = dataframe_to_records(scan_index_frame)

    scans = {}
    if not scan_index_frame.empty:
        for scan_id in scan_index_frame["scan_id"].astype(str).tolist():
            scans[scan_id] = dataframe_to_records(load_scan(scan_id))

    return create_backup_payload(
        watchlist=watchlist,
        scan_index=scan_index,
        scans=scans,
    )


def backup_all() -> dict:
    payload = build_current_backup()
    local_path = save_local_backup(payload)
    cloud_key = save_cloud_backup(payload) if cloud_enabled() else None
    return {
        "local_path": str(local_path),
        "cloud_key": cloud_key,
        "scan_count": len(payload.get("scans", {})),
        "watchlist_count": len(payload.get("watchlist", [])),
    }


def migrate_local_to_cloud() -> dict:
    if not cloud_enabled():
        raise RuntimeError("Cloud storage is not configured.")

    payload = build_current_backup()
    put(WATCHLIST_KEY, payload.get("watchlist", []))
    put(SCAN_INDEX_KEY, payload.get("scan_index", []))

    for scan_id, records in payload.get("scans", {}).items():
        put(f"scan:{scan_id}", records)

    backup_key = save_cloud_backup(payload)
    return {
        "watchlist_count": len(payload.get("watchlist", [])),
        "scan_count": len(payload.get("scans", {})),
        "backup_key": backup_key,
    }


def restore_backup(payload: dict) -> dict:
    if not payload:
        raise RuntimeError("Backup payload is empty.")

    watchlist = pd.DataFrame(payload.get("watchlist", []))
    save_watchlist(watchlist)

    scan_index = payload.get("scan_index", [])
    put(SCAN_INDEX_KEY, scan_index)

    for scan_id, records in payload.get("scans", {}).items():
        put(f"scan:{scan_id}", records)

    return {
        "watchlist_count": len(payload.get("watchlist", [])),
        "scan_count": len(payload.get("scans", {})),
    }


def restore_latest_cloud_backup() -> dict:
    payload = load_cloud_backup("backup:latest")
    if not payload:
        raise RuntimeError("No cloud backup found.")
    return restore_backup(payload)


def load_backup_file(file_or_buffer) -> dict:
    if hasattr(file_or_buffer, "read"):
        raw = file_or_buffer.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    return json.loads(Path(file_or_buffer).read_text(encoding="utf-8"))
