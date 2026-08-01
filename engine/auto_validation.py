from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import math
import os
import tempfile
from typing import Any

import pandas as pd

DEFAULT_PATH = Path("storage/auto_validation/30_day_tracker.json")
TARGET_DAYS = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _num(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return default if math.isnan(number) or math.isinf(number) else number
    except (TypeError, ValueError):
        return default


def new_tracker(started_at: str | None = None) -> dict:
    stamp = started_at or _now_iso()
    return {
        "version": "14.3",
        "programme": "30-Day Automatic Paper Validation",
        "started_at": stamp,
        "target_days": TARGET_DAYS,
        "days": [],
        "trades": [],
        "updated_at": stamp,
        "notes": [
            "Paper-validation only; no broker orders are placed.",
            "Open positions are marked using the latest scan price and close-only target/stop checks.",
        ],
    }


def load_tracker(path: str | Path = DEFAULT_PATH) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else new_tracker()
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return new_tracker()


def save_tracker(tracker: dict, path: str | Path = DEFAULT_PATH) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(tracker, indent=2, default=str)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    os.replace(temp_name, target)
    return target


def _price_map(scan: pd.DataFrame | None) -> dict[str, float]:
    frame = scan if isinstance(scan, pd.DataFrame) else pd.DataFrame()
    if frame.empty or "ticker" not in frame.columns:
        return {}
    price_col = next((c for c in ("latest_price", "current_price", "price", "close", "entry_price") if c in frame.columns), None)
    if not price_col:
        return {}
    output: dict[str, float] = {}
    for _, row in frame.iterrows():
        price = _num(row.get(price_col))
        if price > 0:
            output[str(row.get("ticker", "")).upper()] = price
    return output


def _trade_return(entry: float, exit_price: float) -> float:
    return ((exit_price / entry) - 1.0) * 100.0 if entry > 0 else 0.0


def record_daily_run(
    desk: pd.DataFrame | None,
    scan: pd.DataFrame | None,
    regime: dict | None,
    *,
    run_at: str | None = None,
    maximum_new_positions: int = 2,
    path: str | Path = DEFAULT_PATH,
) -> dict:
    """Update open paper positions and capture today's qualified recommendations once.

    The tracker deliberately uses only information available during each Daily Routine run.
    It never submits broker orders and it does not backfill intraday target/stop touches.
    """
    tracker = load_tracker(path)
    stamp = run_at or _now_iso()
    day = stamp[:10]
    prices = _price_map(scan)

    # Mark existing paper positions with today's latest scan price.
    for trade in tracker.get("trades", []):
        if trade.get("status") != "OPEN":
            continue
        ticker = str(trade.get("ticker", "")).upper()
        price = prices.get(ticker)
        if not price:
            continue
        trade["latest_price"] = round(price, 4)
        trade["last_marked_at"] = stamp
        entry = _num(trade.get("entry_price"))
        target = _num(trade.get("target_price"))
        stop = _num(trade.get("stop_loss"))
        reason = None
        if target > 0 and price >= target:
            reason = "TARGET"
        elif stop > 0 and price <= stop:
            reason = "STOP"
        if reason:
            trade["status"] = "CLOSED"
            trade["exit_reason"] = reason
            trade["exit_price"] = round(price, 4)
            trade["closed_at"] = stamp
            trade["return_pct"] = round(_trade_return(entry, price), 4)

    recorded_days = {str(item.get("date")) for item in tracker.get("days", [])}
    new_trades: list[dict] = []
    frame = desk if isinstance(desk, pd.DataFrame) else pd.DataFrame()
    if day not in recorded_days and not frame.empty:
        status = frame.get("swing_status", pd.Series(index=frame.index, dtype=str)).astype(str)
        qualified = frame[status.isin(["PRIORITY", "QUALIFIED"])].head(maximum_new_positions)
        open_tickers = {str(t.get("ticker", "")).upper() for t in tracker.get("trades", []) if t.get("status") == "OPEN"}
        for _, row in qualified.iterrows():
            ticker = str(row.get("ticker", "")).upper()
            if not ticker or ticker in open_tickers:
                continue
            entry = _num(row.get("entry_price"), prices.get(ticker, 0.0)) or prices.get(ticker, 0.0)
            if entry <= 0:
                continue
            trade = {
                "id": f"{day}-{ticker}",
                "ticker": ticker,
                "opened_at": stamp,
                "entry_price": round(entry, 4),
                "target_price": round(_num(row.get("target_price")), 4),
                "stop_loss": round(_num(row.get("stop_loss")), 4),
                "position_size_pct": round(_num(row.get("position_size_pct")), 2),
                "score": round(_num(row.get("score")), 2),
                "confidence_status": str(row.get("swing_status", "QUALIFIED")),
                "regime": str((regime or {}).get("regime", "UNKNOWN")),
                "status": "OPEN",
                "latest_price": round(prices.get(ticker, entry), 4),
            }
            tracker.setdefault("trades", []).append(trade)
            new_trades.append(trade)
            open_tickers.add(ticker)

        tracker.setdefault("days", []).append({
            "date": day,
            "run_at": stamp,
            "regime": str((regime or {}).get("regime", "UNKNOWN")),
            "qualified_count": int(len(qualified)),
            "new_paper_trades": len(new_trades),
            "verdict": "TRADE" if len(qualified) else "NO TRADE",
        })

    tracker["updated_at"] = stamp
    save_tracker(tracker, path)
    return tracker


def tracker_summary(tracker: dict | None) -> dict:
    tracker = tracker if isinstance(tracker, dict) else new_tracker()
    trades = tracker.get("trades", []) or []
    closed = [t for t in trades if t.get("status") == "CLOSED"]
    open_trades = [t for t in trades if t.get("status") == "OPEN"]
    returns = [_num(t.get("return_pct")) for t in closed]
    gains = sum(value for value in returns if value > 0)
    losses = abs(sum(value for value in returns if value < 0))
    pf = gains / losses if losses > 0 else (999.0 if gains > 0 else 0.0)
    days = len({str(d.get("date")) for d in tracker.get("days", [])})
    win_rate = (sum(1 for value in returns if value > 0) / len(returns) * 100.0) if returns else 0.0
    status = "COMPLETE" if days >= int(tracker.get("target_days", TARGET_DAYS)) else "COLLECTING"
    if len(closed) >= 10:
        status = "ON TRACK" if pf >= 1.2 and sum(returns) > 0 else "REVIEW"
    return {
        "days_completed": days,
        "target_days": int(tracker.get("target_days", TARGET_DAYS)),
        "progress_pct": round(min(days / max(int(tracker.get("target_days", TARGET_DAYS)), 1), 1.0) * 100, 1),
        "trades_total": len(trades),
        "open_trades": len(open_trades),
        "closed_trades": len(closed),
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(pf, 3),
        "total_return_pct": round(sum(returns), 3),
        "status": status,
    }


def reset_tracker(path: str | Path = DEFAULT_PATH) -> dict:
    tracker = new_tracker()
    save_tracker(tracker, path)
    return tracker
