from data import cloud_store


def test_credentials_remove_accidental_whitespace(monkeypatch):
    values = {
        "SUPABASE_URL": " https://abc.supabase.co \n",
        "SUPABASE_KEY": "sb_publishable_abc \n def",
    }
    monkeypatch.setattr(cloud_store, "_secret", lambda name, default="": values.get(name, default))
    config = cloud_store.get_storage_config()
    assert config.url == "https://abc.supabase.co"
    assert config.key == "sb_publishable_abcdef"
    assert config.key_source == "SUPABASE_KEY"
    assert config.key_type == "publishable"


def test_publishable_key_takes_priority_over_secret(monkeypatch):
    values = {
        "SUPABASE_URL": "https://abc.supabase.co",
        "SUPABASE_SECRET_KEY": "sb_secret_server",
        "SUPABASE_KEY": "sb_publishable_client",
    }
    monkeypatch.setattr(cloud_store, "_secret", lambda name, default="": values.get(name, default))
    config = cloud_store.get_storage_config()
    assert config.key == "sb_publishable_client"
    assert config.key_source == "SUPABASE_KEY"
    assert config.key_type == "publishable"
    assert "Multiple Supabase keys" in config.warning


def test_publishable_alias_supported(monkeypatch):
    values = {
        "SUPABASE_URL": "https://abc.supabase.co",
        "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_alias",
    }
    monkeypatch.setattr(cloud_store, "_secret", lambda name, default="": values.get(name, default))
    config = cloud_store.get_storage_config()
    assert config.enabled is True
    assert config.key_source == "SUPABASE_PUBLISHABLE_KEY"
