from __future__ import annotations

import pandas as pd

from alerts.config import AlertConfig
from alerts.models import AlertEvent


SEVERITY_ORDER = {"INFO": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _meets_minimum(severity: str, minimum: str) -> bool:
    return SEVERITY_ORDER.get(severity, 0) >= SEVERITY_ORDER.get(minimum, 2)


def evaluate_signal_changes(comparison: pd.DataFrame, config: AlertConfig) -> list[AlertEvent]:
    if comparison is None or comparison.empty:
        return []
    events: list[AlertEvent] = []
    for _, row in comparison.iterrows():
        ticker = str(row.get("ticker", "")).upper()
        previous = str(row.get("signal_prev", "")).upper()
        current = str(row.get("signal_now", "")).upper()
        if not ticker or not current or current == previous:
            continue
        if config.alert_buy_upgrades and current == "BUY" and previous != "BUY":
            events.append(AlertEvent(
                alert_type="BUY_UPGRADE",
                severity="MEDIUM",
                ticker=ticker,
                title=f"{ticker} upgraded to BUY",
                message=f"Signal changed from {previous or 'NEW'} to BUY.",
                source="scan_comparison",
            ))
        if config.alert_signal_losses and previous == "BUY" and current != "BUY":
            severity = "HIGH" if current in {"AVOID", "SELL"} else "MEDIUM"
            events.append(AlertEvent(
                alert_type="SIGNAL_LOSS",
                severity=severity,
                ticker=ticker,
                title=f"{ticker} lost BUY status",
                message=f"Signal changed from BUY to {current or 'UNKNOWN'}.",
                source="scan_comparison",
            ))
    return [event for event in events if _meets_minimum(event.severity, config.minimum_severity)]


def evaluate_portfolio(monitor: pd.DataFrame, config: AlertConfig) -> list[AlertEvent]:
    if monitor is None or monitor.empty:
        return []
    events: list[AlertEvent] = []
    for _, row in monitor.iterrows():
        ticker = str(row.get("ticker", "")).upper()
        if not ticker:
            continue
        target_distance = pd.to_numeric(row.get("distance_to_target_pct"), errors="coerce")
        stop_distance = pd.to_numeric(row.get("distance_to_stop_pct"), errors="coerce")
        alerts_text = str(row.get("alerts", "")).upper()

        if config.alert_near_stop and pd.notna(stop_distance) and stop_distance <= config.near_stop_pct:
            severity = "CRITICAL" if stop_distance < 0 or "STOP BREACHED" in alerts_text else "HIGH"
            events.append(AlertEvent(
                alert_type="STOP_ALERT",
                severity=severity,
                ticker=ticker,
                title=f"{ticker} is near its stop",
                message=f"Distance to stop: {float(stop_distance):.2f}%.",
                source="portfolio_monitor",
            ))

        if config.alert_near_target and pd.notna(target_distance) and 0 <= target_distance <= config.near_target_pct:
            events.append(AlertEvent(
                alert_type="TARGET_ALERT",
                severity="MEDIUM",
                ticker=ticker,
                title=f"{ticker} is near its target",
                message=f"Distance to target: {float(target_distance):.2f}%.",
                source="portfolio_monitor",
            ))
    return [event for event in events if _meets_minimum(event.severity, config.minimum_severity)]


def evaluate_regime(regime: dict | None, config: AlertConfig) -> list[AlertEvent]:
    if not regime:
        return []
    label = str(regime.get("regime", "UNKNOWN")).upper()
    if label not in {"RISK_OFF", "DEFENSIVE"}:
        return []
    event = AlertEvent(
        alert_type="MARKET_REGIME",
        severity="HIGH",
        title=f"Market regime is {label}",
        message=str(regime.get("reason", "Market conditions have weakened.")),
        source="market_regime",
    )
    return [event] if _meets_minimum(event.severity, config.minimum_severity) else []


def evaluate_alerts(
    comparison: pd.DataFrame | None,
    monitor: pd.DataFrame | None,
    regime: dict | None,
    config: AlertConfig,
) -> list[AlertEvent]:
    if not config.enabled:
        return []
    events = []
    events.extend(evaluate_signal_changes(comparison if comparison is not None else pd.DataFrame(), config))
    events.extend(evaluate_portfolio(monitor if monitor is not None else pd.DataFrame(), config))
    events.extend(evaluate_regime(regime, config))
    unique: dict[str, AlertEvent] = {}
    for event in events:
        normalised = event.normalised()
        unique[normalised.fingerprint] = normalised
    return sorted(unique.values(), key=lambda item: SEVERITY_ORDER.get(item.severity, 0), reverse=True)
