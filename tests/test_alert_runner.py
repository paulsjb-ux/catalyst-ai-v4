from alerts.runner import run_with_retries


class DummyConfig:
    pass


def test_runner_succeeds_after_retry(monkeypatch):
    calls = {"count": 0}
    monkeypatch.setattr("alerts.runner.record_cycle_started", lambda trigger: {})
    monkeypatch.setattr("alerts.runner.record_cycle_finished", lambda result, trigger: {})
    monkeypatch.setattr("alerts.runner.record_cycle_exception", lambda exc, trigger: {})
    monkeypatch.setattr("alerts.runner.time.sleep", lambda seconds: None)

    def cycle(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary")
        return {"event_count": 1, "delivery_count": 1, "deliveries": [{"status": "sent"}]}

    result = run_with_retries(cycle, config=DummyConfig(), max_attempts=3, base_delay_seconds=0)
    assert result["attempts"] == 2
    assert result["event_count"] == 1


def test_runner_raises_after_final_attempt(monkeypatch):
    monkeypatch.setattr("alerts.runner.record_cycle_started", lambda trigger: {})
    monkeypatch.setattr("alerts.runner.record_cycle_exception", lambda exc, trigger: {})
    monkeypatch.setattr("alerts.runner.time.sleep", lambda seconds: None)

    def cycle(**kwargs):
        raise ValueError("broken")

    try:
        run_with_retries(cycle, config=DummyConfig(), max_attempts=2, base_delay_seconds=0)
    except ValueError as exc:
        assert str(exc) == "broken"
    else:
        raise AssertionError("Expected ValueError")
