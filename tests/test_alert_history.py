from alerts.models import AlertEvent


def test_fingerprint_is_stable():
    first = AlertEvent("BUY_UPGRADE", "MEDIUM", "AAPL upgraded", "WATCH to BUY", "AAPL").normalised()
    second = AlertEvent("BUY_UPGRADE", "MEDIUM", "AAPL upgraded", "WATCH to BUY", "aapl").normalised()
    assert first.fingerprint == second.fingerprint
    assert first.ticker == "AAPL"


def test_alert_to_dict_has_timestamp():
    row = AlertEvent("TEST", "INFO", "Test", "Message").to_dict()
    assert row["created_at"]
    assert row["fingerprint"]
