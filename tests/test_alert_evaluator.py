import pandas as pd

from alerts.config import AlertConfig
from alerts.evaluator import evaluate_alerts, evaluate_portfolio, evaluate_signal_changes


def test_buy_upgrade_and_signal_loss():
    comparison = pd.DataFrame({
        "ticker": ["AAPL", "MSFT"],
        "signal_prev": ["WATCH", "BUY"],
        "signal_now": ["BUY", "AVOID"],
    })
    events = evaluate_signal_changes(comparison, AlertConfig())
    assert [event.alert_type for event in events] == ["BUY_UPGRADE", "SIGNAL_LOSS"]
    assert events[1].severity == "HIGH"


def test_target_and_stop_alerts():
    monitor = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "NVDA"],
        "distance_to_target_pct": [2.5, 12.0, 12.0],
        "distance_to_stop_pct": [12.0, 3.0, -1.0],
        "alerts": ["NEAR TARGET", "NEAR STOP", "STOP BREACHED"],
    })
    events = evaluate_portfolio(monitor, AlertConfig())
    assert {event.alert_type for event in events} == {"TARGET_ALERT", "STOP_ALERT"}
    assert any(event.severity == "CRITICAL" for event in events)


def test_disabled_alerts_return_none():
    events = evaluate_alerts(pd.DataFrame(), pd.DataFrame(), {"regime": "RISK_OFF"}, AlertConfig(enabled=False))
    assert events == []
