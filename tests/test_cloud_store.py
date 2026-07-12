from data.cloud_store import create_backup_payload


def test_create_backup_payload():
    payload = create_backup_payload(
        watchlist=[{"ticker": "AAPL"}],
        scan_index=[{"scan_id": "123"}],
        scans={"123": [{"ticker": "AAPL"}]},
    )

    assert payload["schema_version"] == 1
    assert payload["watchlist"][0]["ticker"] == "AAPL"
    assert "created_at" in payload
