from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from alerts.delivery import delivery_readiness
from alerts.config import AlertConfig
from data.storage_service import get_json, put_json

STATUS_KEY = "alert_runtime_status"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_runtime_status() -> dict[str, Any]:
    value = get_json(STATUS_KEY, default={})
    return value if isinstance(value, dict) else {}


def save_runtime_status(status: dict[str, Any]) -> dict[str, Any]:
    payload = {**status, "updated_at": _now()}
    put_json(STATUS_KEY, payload)
    return payload


def record_cycle_started(trigger: str = "manual") -> dict[str, Any]:
    current = load_runtime_status()
    return save_runtime_status({
        **current,
        "last_started_at": _now(),
        "last_trigger": trigger,
        "last_status": "running",
    })


def record_cycle_finished(result: dict[str, Any], trigger: str = "manual") -> dict[str, Any]:
    deliveries = result.get("deliveries", []) or []
    failures = [item for item in deliveries if item.get("status") == "failed"]
    sent = [item for item in deliveries if item.get("status") == "sent"]
    skipped = [item for item in deliveries if item.get("status") == "skipped"]
    status = "failed" if failures else "success"
    return save_runtime_status({
        "last_finished_at": _now(),
        "last_trigger": trigger,
        "last_status": status,
        "last_event_count": int(result.get("event_count", 0)),
        "last_delivery_count": int(result.get("delivery_count", 0)),
        "last_sent_count": len(sent),
        "last_failed_count": len(failures),
        "last_skipped_count": len(skipped),
        "last_quiet": bool(result.get("quiet", False)),
        "last_error": failures[0].get("detail", "") if failures else "",
    })


def record_cycle_exception(exc: Exception, trigger: str = "manual") -> dict[str, Any]:
    return save_runtime_status({
        "last_finished_at": _now(),
        "last_trigger": trigger,
        "last_status": "failed",
        "last_event_count": 0,
        "last_delivery_count": 0,
        "last_sent_count": 0,
        "last_failed_count": 1,
        "last_skipped_count": 0,
        "last_quiet": False,
        "last_error": str(exc),
    })


def scheduler_health(config: AlertConfig) -> dict[str, Any]:
    runtime = load_runtime_status()
    readiness = delivery_readiness(config)
    return {
        "alerts_enabled": bool(config.enabled),
        "delivery_ready": bool(readiness.get("any_ready")),
        "email_ready": bool(readiness.get("email_ready")),
        "webhook_ready": bool(readiness.get("webhook_ready")),
        "last_status": runtime.get("last_status", "never run"),
        "last_finished_at": runtime.get("last_finished_at", ""),
        "last_trigger": runtime.get("last_trigger", ""),
        "last_sent_count": runtime.get("last_sent_count", 0),
        "last_failed_count": runtime.get("last_failed_count", 0),
        "last_error": runtime.get("last_error", ""),
    }
