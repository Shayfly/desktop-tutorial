import pytest

from live_core.config import ConfigurationError, Settings


def test_production_requires_database_url(monkeypatch):
    monkeypatch.setenv("OMNI_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        Settings.from_env()


def test_local_mode_allows_memory_store(monkeypatch):
    monkeypatch.setenv("OMNI_ENV", "development")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings.from_env()
    assert settings.persistence == "memory"
