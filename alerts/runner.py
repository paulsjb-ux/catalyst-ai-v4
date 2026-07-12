from __future__ import annotations

import time
from typing import Callable

from alerts.config import AlertConfig, load_alert_config
from alerts.health import record_cycle_exception, record_cycle_finished, record_cycle_started
from alerts.service import run_alert_cycle


def run_with_retries(
    cycle: Callable[..., dict],
    *,
    comparison=None,
    monitor=None,
    regime=None,
    config: AlertConfig | None = None,
    trigger: str = "manual",
    max_attempts: int = 3,
    base_delay_seconds: float = 2.0,
) -> dict:
    active_config = config or load_alert_config()
    record_cycle_started(trigger)
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = cycle(
                comparison=comparison,
                monitor=monitor,
                regime=regime,
                config=active_config,
                send=True,
            )
            result["attempts"] = attempt
            result["trigger"] = trigger
            record_cycle_finished(result, trigger)
            return result
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                time.sleep(base_delay_seconds * attempt)

    assert last_error is not None
    record_cycle_exception(last_error, trigger)
    raise last_error


def run_alert_job(*, comparison=None, monitor=None, regime=None, config: AlertConfig | None = None, trigger: str = "manual") -> dict:
    return run_with_retries(
        run_alert_cycle,
        comparison=comparison,
        monitor=monitor,
        regime=regime,
        config=config,
        trigger=trigger,
    )
