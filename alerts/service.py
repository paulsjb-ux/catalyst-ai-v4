from __future__ import annotations

import pandas as pd

from alerts.config import AlertConfig, load_alert_config
from alerts.delivery import deliver_events
from alerts.evaluator import evaluate_alerts
from alerts.history import save_alerts


def run_alert_cycle(
    comparison: pd.DataFrame | None = None,
    monitor: pd.DataFrame | None = None,
    regime: dict | None = None,
    config: AlertConfig | None = None,
    send: bool = True,
) -> dict:
    active_config = config or load_alert_config()
    events = evaluate_alerts(comparison, monitor, regime, active_config)
    saved_count = save_alerts(events)

    should_send = send and (not active_config.quiet_mode or bool(events))
    deliveries = deliver_events(events, active_config) if should_send else []
    return {
        "event_count": len(events),
        "saved_count": saved_count,
        "delivery_count": len(deliveries),
        "events": [event.to_dict() for event in events],
        "deliveries": deliveries,
        "quiet": active_config.quiet_mode and not events,
    }
