from alerts.config import AlertConfig
from alerts.health import record_cycle_finished, scheduler_health


def test_record_cycle_finished_summarises_delivery(monkeypatch):
    saved = {}
    monkeypatch.setattr("alerts.health.save_runtime_status", lambda payload: saved.update(payload) or payload)
    result = {
        "event_count": 2,
        "delivery_count": 2,
        "deliveries": [
            {"status": "sent"},
            {"status": "failed", "detail": "smtp down"},
        ],
        "quiet": False,
    }
    payload = record_cycle_finished(result, "test")
    assert payload["last_status"] == "failed"
    assert payload["last_sent_count"] == 1
    assert payload["last_failed_count"] == 1
    assert payload["last_error"] == "smtp down"


def test_scheduler_health_combines_readiness(monkeypatch):
    monkeypatch.setattr("alerts.health.load_runtime_status", lambda: {"last_status": "success", "last_sent_count": 1})
    monkeypatch.setattr("alerts.health.delivery_readiness", lambda config: {"any_ready": True, "email_ready": True, "webhook_ready": False})
    health = scheduler_health(AlertConfig())
    assert health["delivery_ready"] is True
    assert health["last_status"] == "success"
