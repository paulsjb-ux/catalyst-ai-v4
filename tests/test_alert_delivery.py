from alerts.config import AlertConfig
from alerts.delivery import delivery_readiness


def test_delivery_not_ready_without_secrets(monkeypatch):
    for name in ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "ALERT_WEBHOOK_URL"]:
        monkeypatch.delenv(name, raising=False)
    status = delivery_readiness(AlertConfig(email_enabled=True, webhook_enabled=True, recipient_email="a@example.com"))
    assert status["any_ready"] is False


def test_webhook_ready_with_secret(monkeypatch):
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://example.com/hook")
    status = delivery_readiness(AlertConfig(webhook_enabled=True))
    assert status["webhook_ready"] is True
