from data import cloud_store


def _config(key: str = "sb_publishable_example") -> cloud_store.StorageConfig:
    return cloud_store.StorageConfig("https://example.supabase.co", key, True)


def test_read_cache_avoids_duplicate_requests(monkeypatch):
    cloud_store.clear_cache()
    monkeypatch.setattr(cloud_store, "get_storage_config", lambda: _config())
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url))
        return 200, [{"value": {"saved": True}}]

    monkeypatch.setattr(cloud_store, "_request", fake_request)
    assert cloud_store.get_json("watchlist") == {"saved": True}
    assert cloud_store.get_json("watchlist") == {"saved": True}
    assert len(calls) == 1


def test_put_updates_read_cache(monkeypatch):
    cloud_store.clear_cache()
    monkeypatch.setattr(cloud_store, "get_storage_config", lambda: _config())
    monkeypatch.setattr(cloud_store, "_request", lambda *args, **kwargs: (201, None))

    cloud_store.put_json("watchlist", [{"ticker": "AAPL"}])
    assert cloud_store.get_json("watchlist") == [{"ticker": "AAPL"}]


def test_health_check_verifies_write_and_read(monkeypatch):
    cloud_store.clear_cache()
    monkeypatch.setattr(cloud_store, "get_storage_config", lambda: _config())
    stored = {}

    def fake_request(method, url, payload=None, **kwargs):
        if method == "GET" and "select=key" in url:
            return 200, []
        if method == "POST":
            stored[payload["key"]] = payload["value"]
            return 201, None
        if method == "GET" and "select=value" in url:
            return 200, [{"value": stored["__catalyst_healthcheck__"]}]
        if method == "DELETE":
            stored.clear()
            return 204, None
        raise AssertionError((method, url))

    monkeypatch.setattr(cloud_store, "_request", fake_request)
    result = cloud_store.health_check(force=True)
    assert result["reachable"] is True
    assert result["table_ready"] is True
    assert result["read_ready"] is True
    assert result["write_ready"] is True
    assert result["error"] is None


def test_friendly_401_message():
    message = str(cloud_store._friendly_http_error(401, '{"message":"Invalid API key"}'))
    assert "SUPABASE_URL" in message
    assert "same project" in message
