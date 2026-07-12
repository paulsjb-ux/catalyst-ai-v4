from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from alerts.models import AlertEvent
from data.storage_service import get, put


ALERT_HISTORY_KEY = "alert_history"
DELIVERY_HISTORY_KEY = "alert_delivery_history"
MAX_HISTORY = 500


def load_alert_history() -> list[dict]:
    value = get(ALERT_HISTORY_KEY, [])
    return value if isinstance(value, list) else []


def alert_history_frame() -> pd.DataFrame:
    rows = load_alert_history()
    if not rows:
        return pd.DataFrame(columns=[
            "created_at", "severity", "alert_type", "ticker", "title", "message", "fingerprint"
        ])
    return pd.DataFrame(rows).sort_values("created_at", ascending=False).reset_index(drop=True)


def save_alerts(events: list[AlertEvent]) -> int:
    if not events:
        return 0
    history = load_alert_history()
    existing = {item.get("fingerprint") for item in history}
    added = 0
    for event in events:
        row = event.to_dict()
        if row["fingerprint"] in existing:
            continue
        history.append(row)
        existing.add(row["fingerprint"])
        added += 1
    put(ALERT_HISTORY_KEY, history[-MAX_HISTORY:])
    return added


def recently_sent(fingerprint: str, hours: int = 24) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, hours))
    for item in load_delivery_history():
        if item.get("fingerprint") != fingerprint:
            continue
        try:
            sent_at = datetime.fromisoformat(str(item.get("sent_at", "")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if sent_at >= cutoff and item.get("status") == "sent":
            return True
    return False


def load_delivery_history() -> list[dict]:
    value = get(DELIVERY_HISTORY_KEY, [])
    return value if isinstance(value, list) else []


def record_delivery(event: AlertEvent, channel: str, status: str, detail: str = "") -> None:
    history = load_delivery_history()
    row = event.to_dict()
    history.append({
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": row["fingerprint"],
        "alert_type": row["alert_type"],
        "ticker": row["ticker"],
        "channel": channel,
        "status": status,
        "detail": detail[:500],
    })
    put(DELIVERY_HISTORY_KEY, history[-MAX_HISTORY:])


def delivery_history_frame() -> pd.DataFrame:
    rows = load_delivery_history()
    if not rows:
        return pd.DataFrame(columns=[
            "sent_at", "status", "channel", "alert_type", "ticker", "detail"
        ])
    return pd.DataFrame(rows).sort_values("sent_at", ascending=False).reset_index(drop=True)
