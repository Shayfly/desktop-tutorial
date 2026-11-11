import pytest

from live_core.config import ConfigurationError, Settings


def _clear(monkeypatch):
    for name in ("OMNI_DATABASE_URL", "DATABASE_URL", "OMNI_LIVE_PERSISTENCE", "OMNI_ENV"):
        monkeypatch.delenv(name, raising=False)


def test_production_requires_omni_database_url(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("OMNI_ENV", "production")
    with pytest.raises(ConfigurationError, match="OMNI_DATABASE_URL"):
        Settings.from_env()


def test_database_url_is_never_read(monkeypatch):
    # DATABASE_URL alone must not satisfy live_core: it may point at a suspended database.
    _clear(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://old-host/old-db")
    with pytest.raises(ConfigurationError, match="DATABASE_URL is not read"):
        Settings.from_env()


def test_unset_omni_env_is_not_permission_for_memory(monkeypatch):
    _clear(monkeypatch)
    with pytest.raises(ConfigurationError, match="OMNI_DATABASE_URL"):
        Settings.from_env()


def test_omni_database_url_selects_postgres(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("OMNI_DATABASE_URL", "postgresql://new-host/new-db")
    monkeypatch.setenv("DATABASE_URL", "postgresql://old-host/old-db")
    settings = Settings.from_env()
    assert settings.persistence == "postgres"
    assert settings.database_url == "postgresql://new-host/new-db"


def test_memory_only_when_requested_by_name(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("OMNI_LIVE_PERSISTENCE", "memory")
    settings = Settings.from_env()
    assert settings.persistence == "memory"


def test_memory_request_is_refused_in_production(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("OMNI_ENV", "production")
    monkeypatch.setenv("OMNI_LIVE_PERSISTENCE", "memory")
    with pytest.raises(ConfigurationError):
        Settings.from_env()
