from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd

from data.storage_service import dataframe_to_records, get, put, records_to_dataframe

RUN_HISTORY_KEY = "release_candidate:routine_history"
RECOMMENDATIONS_KEY = "release_candidate:recommendations"
MAX_RUN_HISTORY = 180
MAX_RECOMMENDATION_HISTORY = 2000
DEFAULT_EXPIRY_TRADING_DAYS = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


def add_trading_days(start: date, days: int) -> date:
    current = start
    remaining = max(0, int(days))
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def load_run_history() -> pd.DataFrame:
    return records_to_dataframe(get(RUN_HISTORY_KEY, []))


def record_routine_history(summary: dict[str, Any], regime: dict[str, Any], desk: pd.DataFrame) -> None:
    rows = get(RUN_HISTORY_KEY, [])
    rows = rows if isinstance(rows, list) else []
    finished_at = str(summary.get("finished_at") or _now_iso())
    qualified = 0
    if isinstance(desk, pd.DataFrame) and not desk.empty and "swing_status" in desk.columns:
        qualified = int(desk["swing_status"].astype(str).str.upper().eq("QUALIFIED").sum())
    record = {
        "finished_at": finished_at,
        "date": finished_at[:10],
        "regime": str((regime or {}).get("regime", "UNKNOWN")),
        "market_score": (regime or {}).get("market_score"),
        "symbols_scanned": summary.get("symbols_scanned", summary.get("scanned", 0)),
        "buy_count": summary.get("buy_count", 0),
        "watch_count": summary.get("watch_count", 0),
        "qualified_count": qualified,
        "proof_verdict": summary.get("proof_verdict", "UNKNOWN"),
        "duration_seconds": summary.get("duration_seconds", 0),
        "success": bool(summary.get("success", True)),
    }
    # One durable audit row per completed routine timestamp. Re-runs remain visible.
    if not any(str(item.get("finished_at")) == finished_at for item in rows if isinstance(item, dict)):
        rows.append(record)
    put(RUN_HISTORY_KEY, rows[-MAX_RUN_HISTORY:])


def record_recommendations(
    desk: pd.DataFrame,
    *,
    run_at: str | None = None,
    expiry_trading_days: int = DEFAULT_EXPIRY_TRADING_DAYS,
) -> None:
    if desk is None or desk.empty:
        return
    run_at = run_at or _now_iso()
    run_day = _as_date(run_at) or date.today()
    expires = add_trading_days(run_day, expiry_trading_days).isoformat()
    existing = get(RECOMMENDATIONS_KEY, [])
    existing = existing if isinstance(existing, list) else []

    wanted = [
        "daily_rank", "ticker", "action", "score", "swing_status", "position_size_pct",
        "entry_price", "target_price", "stop_loss", "risk_reward", "trend",
    ]
    for row in dataframe_to_records(desk[[c for c in wanted if c in desk.columns]]):
        ticker = str(row.get("ticker", "")).upper().strip()
        if not ticker:
            continue
        existing.append({
            **row,
            "ticker": ticker,
            "recommended_at": run_at,
            "recommended_date": run_day.isoformat(),
            "expires_date": expires,
            "expiry_trading_days": int(expiry_trading_days),
        })
    put(RECOMMENDATIONS_KEY, existing[-MAX_RECOMMENDATION_HISTORY:])


def recommendation_history(as_of: date | None = None) -> pd.DataFrame:
    frame = records_to_dataframe(get(RECOMMENDATIONS_KEY, []))
    if frame.empty:
        return frame
    as_of = as_of or date.today()
    expiry = pd.to_datetime(frame.get("expires_date"), errors="coerce").dt.date
    frame["lifecycle"] = ["ACTIVE" if pd.notna(day) and day >= as_of else "EXPIRED" for day in expiry]
    return frame.sort_values("recommended_at", ascending=False, kind="stable").reset_index(drop=True)


def active_recommendations(as_of: date | None = None) -> pd.DataFrame:
    frame = recommendation_history(as_of)
    if frame.empty:
        return frame
    active = frame[frame["lifecycle"].eq("ACTIVE")].copy()
    # Newest recommendation wins when the same ticker appears on several runs.
    active = active.drop_duplicates("ticker", keep="first")
    if "daily_rank" in active.columns:
        active["daily_rank"] = pd.to_numeric(active["daily_rank"], errors="coerce")
        active = active.sort_values(["recommended_date", "daily_rank"], ascending=[False, True], kind="stable")
    return active.reset_index(drop=True)
