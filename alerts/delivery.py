from __future__ import annotations

from email.message import EmailMessage
import json
import os
import smtplib
import urllib.request

from alerts.config import AlertConfig
from alerts.history import record_delivery, recently_sent
from alerts.models import AlertEvent


def _secret(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value:
        return value
    try:
        import streamlit as st
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def delivery_readiness(config: AlertConfig) -> dict:
    email_ready = bool(
        config.email_enabled
        and config.recipient_email
        and _secret("SMTP_HOST")
        and _secret("SMTP_USERNAME")
        and _secret("SMTP_PASSWORD")
    )
    webhook_ready = bool(config.webhook_enabled and _secret("ALERT_WEBHOOK_URL"))
    return {
        "email_ready": email_ready,
        "webhook_ready": webhook_ready,
        "any_ready": email_ready or webhook_ready,
    }


def _send_email(event: AlertEvent, recipient: str) -> None:
    host = _secret("SMTP_HOST")
    port = int(_secret("SMTP_PORT", "587"))
    username = _secret("SMTP_USERNAME")
    password = _secret("SMTP_PASSWORD")
    sender = _secret("SMTP_FROM", username)
    use_tls = _secret("SMTP_USE_TLS", "true").lower() not in {"0", "false", "no"}

    message = EmailMessage()
    message["Subject"] = f"Catalyst AI [{event.severity}] {event.title}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"{event.title}\n\n{event.message}\n\n"
        f"Ticker: {event.ticker or 'N/A'}\n"
        f"Type: {event.alert_type}\n"
        f"Created: {event.created_at}\n"
    )

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)


def _send_webhook(event: AlertEvent) -> None:
    url = _secret("ALERT_WEBHOOK_URL")
    payload = json.dumps(event.to_dict()).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status >= 300:
            raise RuntimeError(f"Webhook returned HTTP {response.status}")


def deliver_event(event: AlertEvent, config: AlertConfig, force: bool = False) -> list[dict]:
    event = event.normalised()
    if not force and recently_sent(event.fingerprint, config.dedupe_hours):
        return [{"channel": "dedupe", "status": "skipped", "detail": "Recently sent"}]

    readiness = delivery_readiness(config)
    results: list[dict] = []

    if readiness["email_ready"]:
        try:
            _send_email(event, config.recipient_email)
            record_delivery(event, "email", "sent")
            results.append({"channel": "email", "status": "sent", "detail": ""})
        except Exception as exc:
            record_delivery(event, "email", "failed", str(exc))
            results.append({"channel": "email", "status": "failed", "detail": str(exc)})

    if readiness["webhook_ready"]:
        try:
            _send_webhook(event)
            record_delivery(event, "webhook", "sent")
            results.append({"channel": "webhook", "status": "sent", "detail": ""})
        except Exception as exc:
            record_delivery(event, "webhook", "failed", str(exc))
            results.append({"channel": "webhook", "status": "failed", "detail": str(exc)})

    if not results:
        record_delivery(event, "none", "skipped", "No delivery channel configured")
        results.append({"channel": "none", "status": "skipped", "detail": "No delivery channel configured"})
    return results


def deliver_events(events: list[AlertEvent], config: AlertConfig, force: bool = False) -> list[dict]:
    outcomes = []
    for event in events:
        for result in deliver_event(event, config, force=force):
            outcomes.append({**event.to_dict(), **result})
    return outcomes
