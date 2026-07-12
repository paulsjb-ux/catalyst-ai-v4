from __future__ import annotations

from dataclasses import asdict, dataclass

from data.storage_service import get, put


ALERT_CONFIG_KEY = "alert_config"


@dataclass
class AlertConfig:
    enabled: bool = True
    quiet_mode: bool = True
    send_daily_brief: bool = True
    alert_buy_upgrades: bool = True
    alert_signal_losses: bool = True
    alert_near_target: bool = True
    alert_near_stop: bool = True
    near_target_pct: float = 5.0
    near_stop_pct: float = 5.0
    minimum_severity: str = "MEDIUM"
    email_enabled: bool = False
    webhook_enabled: bool = False
    recipient_email: str = ""
    delivery_hour_utc: int = 7
    dedupe_hours: int = 24


def load_alert_config() -> AlertConfig:
    raw = get(ALERT_CONFIG_KEY, {})
    if not isinstance(raw, dict):
        return AlertConfig()
    allowed = AlertConfig.__dataclass_fields__.keys()
    values = {key: value for key, value in raw.items() if key in allowed}
    try:
        return AlertConfig(**values)
    except (TypeError, ValueError):
        return AlertConfig()


def save_alert_config(config: AlertConfig) -> str:
    return put(ALERT_CONFIG_KEY, asdict(config))
