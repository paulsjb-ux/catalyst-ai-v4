from data import cloud_store


def _config(key: str) -> cloud_store.StorageConfig:
    return cloud_store.StorageConfig(
        url="https://example.supabase.co",
        key=key,
        enabled=True,
    )


def test_publishable_key_is_not_sent_as_bearer(monkeypatch):
    monkeypatch.setattr(
        cloud_store,
        "get_storage_config",
        lambda: _config("sb_publishable_example"),
    )
    headers = cloud_store._headers()
    assert headers["apikey"] == "sb_publishable_example"
    assert "Authorization" not in headers


def test_secret_key_is_not_sent_as_bearer(monkeypatch):
    monkeypatch.setattr(
        cloud_store,
        "get_storage_config",
        lambda: _config("sb_secret_example"),
    )
    headers = cloud_store._headers()
    assert headers["apikey"] == "sb_secret_example"
    assert "Authorization" not in headers


def test_legacy_jwt_key_keeps_bearer_header(monkeypatch):
    key = "eyJhbGciOiJIUzI1NiJ9.example.signature"
    monkeypatch.setattr(
        cloud_store,
        "get_storage_config",
        lambda: _config(key),
    )
    headers = cloud_store._headers(prefer="return=minimal")
    assert headers["apikey"] == key
    assert headers["Authorization"] == f"Bearer {key}"
    assert headers["Prefer"] == "return=minimal"
