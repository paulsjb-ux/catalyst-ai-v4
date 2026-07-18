from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from data.storage_service import dataframe_to_records, get, put, records_to_dataframe


DATA_DIR = Path("data/local")
WATCHLIST_FILE = DATA_DIR / "watchlist.csv"
WATCHLIST_KEY = "watchlist"

WATCHLIST_COLUMNS = [
    "ticker",
    "quantity",
    "entry_price",
    "target_price",
    "stop_loss",
    "notes",
    "added_at",
]


def _empty_watchlist() -> pd.DataFrame:
    return pd.DataFrame(columns=WATCHLIST_COLUMNS)


def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_watchlist()

    output = frame.copy()
    output.columns = [str(col).strip().lower() for col in output.columns]
    aliases = {
        "symbol": "ticker",
        "shares": "quantity",
        "qty": "quantity",
        "average_price": "entry_price",
        "avg_price": "entry_price",
        "average entry": "entry_price",
        "target": "target_price",
        "stop": "stop_loss",
        "comment": "notes",
    }
    output = output.rename(columns={k: v for k, v in aliases.items() if k in output.columns})

    for column in WATCHLIST_COLUMNS:
        if column not in output.columns:
            output[column] = None

    output["ticker"] = output["ticker"].fillna("").astype(str).str.upper().str.strip()
    output = output[output["ticker"] != ""].copy()

    for column in ["quantity", "entry_price", "target_price", "stop_loss"]:
        output[column] = pd.to_numeric(output[column], errors="coerce")

    output["quantity"] = output["quantity"].fillna(0.0)
    output["notes"] = output["notes"].fillna("").astype(str)
    output["added_at"] = output["added_at"].fillna(datetime.now(timezone.utc).isoformat())
    output = output.drop_duplicates(subset=["ticker"], keep="last")
    return output[WATCHLIST_COLUMNS].sort_values("ticker").reset_index(drop=True)


def load_watchlist() -> pd.DataFrame:
    records = get(WATCHLIST_KEY, None)
    if isinstance(records, list):
        return _normalise(records_to_dataframe(records, WATCHLIST_COLUMNS))

    if not WATCHLIST_FILE.exists():
        return _empty_watchlist()

    try:
        frame = _normalise(pd.read_csv(WATCHLIST_FILE))
        put(WATCHLIST_KEY, dataframe_to_records(frame))
        return frame
    except Exception:
        return _empty_watchlist()


def save_watchlist(frame: pd.DataFrame) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    normalised = _normalise(frame)
    normalised.to_csv(WATCHLIST_FILE, index=False)
    put(WATCHLIST_KEY, dataframe_to_records(normalised))
    return WATCHLIST_FILE


def add_or_update_item(
    ticker: str,
    quantity: float = 0.0,
    entry_price: float | None = None,
    target_price: float | None = None,
    stop_loss: float | None = None,
    notes: str = "",
) -> pd.DataFrame:
    ticker = str(ticker).upper().strip()
    if not ticker:
        return load_watchlist()

    frame = load_watchlist()
    new_row = pd.DataFrame([{
        "ticker": ticker,
        "quantity": quantity or 0.0,
        "entry_price": entry_price,
        "target_price": target_price,
        "stop_loss": stop_loss,
        "notes": notes or "",
        "added_at": datetime.now(timezone.utc).isoformat(),
    }])

    updated = new_row if frame.empty else pd.concat(
        [frame[frame["ticker"] != ticker], new_row],
        ignore_index=True,
    )
    save_watchlist(updated)
    return load_watchlist()


def remove_item(ticker: str) -> pd.DataFrame:
    ticker = str(ticker).upper().strip()
    frame = load_watchlist()
    if frame.empty:
        return frame
    updated = frame[frame["ticker"] != ticker].copy()
    save_watchlist(updated)
    return load_watchlist()


def import_watchlist_csv(file_or_buffer) -> pd.DataFrame:
    imported = _normalise(pd.read_csv(file_or_buffer))
    existing = load_watchlist()
    combined = pd.concat([existing, imported], ignore_index=True)
    save_watchlist(combined)
    return load_watchlist()


def clear_watchlist() -> pd.DataFrame:
    save_watchlist(_empty_watchlist())
    return _empty_watchlist()
