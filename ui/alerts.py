from __future__ import annotations

import pandas as pd
import streamlit as st

from alerts.config import AlertConfig, load_alert_config, save_alert_config
from alerts.delivery import delivery_readiness, deliver_event
from alerts.history import alert_history_frame, delivery_history_frame
from alerts.health import scheduler_health
from alerts.runner import run_alert_job
from alerts.models import AlertEvent
from alerts.service import run_alert_cycle
from data.alert_store import load_market_regime, load_portfolio_monitor, save_market_regime, save_portfolio_monitor
from data.history_store import compare_scans, load_latest_scan, load_previous_scan
from ui.components import section_header


def _current_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    latest = load_latest_scan()
    current_scan_id = None
    if not latest.empty and "scan_id" in latest.columns:
        current_scan_id = str(latest.iloc[0]["scan_id"])
    previous = load_previous_scan(current_scan_id)
    comparison = compare_scans(latest, previous)

    monitor = st.session_state.get("portfolio_monitor", pd.DataFrame())
    if monitor is None or monitor.empty:
        monitor = load_portfolio_monitor()
    else:
        save_portfolio_monitor(monitor)

    regime = st.session_state.get("market_regime") or load_market_regime()
    if regime:
        save_market_regime(regime)
    return comparison, monitor, regime


def _config_form(config: AlertConfig) -> AlertConfig:
    with st.form("alert_config_form"):
        st.markdown("### Alert Rules")
        c1, c2, c3 = st.columns(3)
        enabled = c1.toggle("Alerts enabled", value=config.enabled)
        quiet_mode = c2.toggle("Quiet mode", value=config.quiet_mode, help="Send nothing when there are no meaningful changes.")
        send_daily_brief = c3.toggle("Daily brief delivery", value=config.send_daily_brief)

        c1, c2 = st.columns(2)
        buy_upgrades = c1.toggle("BUY upgrades", value=config.alert_buy_upgrades)
        signal_losses = c2.toggle("BUY signal losses", value=config.alert_signal_losses)
        c3, c4 = st.columns(2)
        near_target = c3.toggle("Near target", value=config.alert_near_target)
        near_stop = c4.toggle("Near stop", value=config.alert_near_stop)

        c1, c2, c3 = st.columns(3)
        target_pct = c1.number_input("Near-target threshold %", 0.5, 20.0, float(config.near_target_pct), 0.5)
        stop_pct = c2.number_input("Near-stop threshold %", 0.5, 20.0, float(config.near_stop_pct), 0.5)
        minimum = c3.selectbox("Minimum severity", ["INFO", "MEDIUM", "HIGH", "CRITICAL"], index=["INFO", "MEDIUM", "HIGH", "CRITICAL"].index(config.minimum_severity if config.minimum_severity in ["INFO", "MEDIUM", "HIGH", "CRITICAL"] else "MEDIUM"))

        st.markdown("### Delivery")
        c1, c2 = st.columns(2)
        email_enabled = c1.toggle("Email", value=config.email_enabled)
        webhook_enabled = c2.toggle("Webhook", value=config.webhook_enabled)
        recipient = st.text_input("Recipient email", value=config.recipient_email)
        c1, c2 = st.columns(2)
        hour = c1.number_input("Daily delivery hour (UTC)", 0, 23, int(config.delivery_hour_utc), 1)
        dedupe = c2.number_input("Duplicate protection (hours)", 1, 168, int(config.dedupe_hours), 1)

        submitted = st.form_submit_button("Save alert settings", use_container_width=True)
        updated = AlertConfig(
            enabled=enabled,
            quiet_mode=quiet_mode,
            send_daily_brief=send_daily_brief,
            alert_buy_upgrades=buy_upgrades,
            alert_signal_losses=signal_losses,
            alert_near_target=near_target,
            alert_near_stop=near_stop,
            near_target_pct=float(target_pct),
            near_stop_pct=float(stop_pct),
            minimum_severity=minimum,
            email_enabled=email_enabled,
            webhook_enabled=webhook_enabled,
            recipient_email=recipient.strip(),
            delivery_hour_utc=int(hour),
            dedupe_hours=int(dedupe),
        )
        if submitted:
            save_alert_config(updated)
            st.success("Alert settings saved to persistent storage.")
        return updated if submitted else config


def render_alerts() -> None:
    section_header(
        "Automated Alerts",
        "Configure meaningful notifications, test delivery and review alert history.",
    )
    config = _config_form(load_alert_config())
    readiness = delivery_readiness(config)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Alerts", "On" if config.enabled else "Off")
    c2.metric("Quiet Mode", "On" if config.quiet_mode else "Off")
    c3.metric("Email Ready", "Yes" if readiness["email_ready"] else "No")
    c4.metric("Webhook Ready", "Yes" if readiness["webhook_ready"] else "No")

    if not readiness["any_ready"]:
        st.info("Alert rules work now. Add email or webhook secrets to enable external delivery.")


    st.markdown("### Scheduler & Delivery Health")
    health = scheduler_health(config)
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Scheduler Status", str(health["last_status"]).title())
    h2.metric("Delivery Ready", "Yes" if health["delivery_ready"] else "No")
    h3.metric("Last Sent", health["last_sent_count"])
    h4.metric("Last Failed", health["last_failed_count"])
    if health["last_finished_at"]:
        st.caption(f"Last completed: {health['last_finished_at']} · Trigger: {health['last_trigger'] or 'unknown'}")
    else:
        st.caption("No scheduled alert cycle has completed yet.")
    if health["last_error"]:
        st.error(f"Last delivery error: {health['last_error']}")

    c1, c2 = st.columns(2)
    if c1.button("Evaluate alerts now", use_container_width=True):
        comparison, monitor, regime = _current_inputs()
        result = run_alert_job(comparison=comparison, monitor=monitor, regime=regime, config=config, trigger="manual_ui")
        if result["quiet"]:
            st.success("Quiet mode: nothing important changed, so no notification was sent.")
        elif result["event_count"]:
            st.success(f"Created {result['event_count']} alert(s); {result['delivery_count']} delivery result(s).")
            st.json(result)
        else:
            st.info("No alert conditions were triggered.")

    if c2.button("Send test notification", use_container_width=True):
        test_event = AlertEvent(
            alert_type="TEST",
            severity="INFO",
            title="Catalyst AI test notification",
            message="Your Sprint 3 Part 3 delivery channel is working.",
        )
        results = deliver_event(test_event, config, force=True)
        if any(item["status"] == "sent" for item in results):
            st.success("Test notification sent.")
        else:
            st.warning("No test notification was sent. Check the delivery secrets below.")
        st.json(results)


    with st.expander("Live scheduler setup"):
        st.markdown("1. Add the required GitHub repository secrets.\n2. Enable the included workflow.\n3. Run it manually once.\n4. Confirm this page shows **Scheduler Status: Success**.")
        st.code("python3 scripts/run_daily_alerts.py --trigger manual_test", language="bash")
        st.caption("The GitHub Actions workflow runs at 08:00 UTC Monday to Friday and can also be started manually.")

    with st.expander("Required Streamlit secrets"):
        st.code('''# Email via SMTP\nSMTP_HOST = "smtp.example.com"\nSMTP_PORT = "587"\nSMTP_USERNAME = "your-user"\nSMTP_PASSWORD = "your-password"\nSMTP_FROM = "alerts@example.com"\nSMTP_USE_TLS = "true"\n\n# Optional webhook\nALERT_WEBHOOK_URL = "https://..."''', language="toml")
        st.caption("Keep these in Streamlit Secrets. Never commit them to GitHub.")

    st.markdown("### Alert History")
    history = alert_history_frame()
    if history.empty:
        st.caption("No alerts recorded yet.")
    else:
        st.dataframe(history, use_container_width=True, hide_index=True)

    st.markdown("### Delivery History")
    deliveries = delivery_history_frame()
    if deliveries.empty:
        st.caption("No delivery attempts recorded yet.")
    else:
        st.dataframe(deliveries, use_container_width=True, hide_index=True)
