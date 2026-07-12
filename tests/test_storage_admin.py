from data.storage_admin import restore_backup


def test_restore_backup_uses_storage_service(monkeypatch):
    calls = []

    monkeypatch.setattr("data.storage_admin.save_watchlist", lambda frame: calls.append(("watchlist", len(frame))))
    monkeypatch.setattr("data.storage_admin.put", lambda key, value: calls.append((key, value)))

    payload = {
        "watchlist": [{"ticker": "AAPL"}],
        "scan_index": [{"scan_id": "123"}],
        "scans": {"123": [{"ticker": "AAPL"}]},
    }

    result = restore_backup(payload)

    assert result["watchlist_count"] == 1
    assert result["scan_count"] == 1
    assert any(call[0] == "scan_index" for call in calls)
    assert any(call[0] == "scan:123" for call in calls)
