from __future__ import annotations

from dataclasses import dataclass
import os


class ConfigurationError(RuntimeError):
    """Raised when production configuration is unsafe or incomplete."""


@dataclass(frozen=True)
class Settings:
    env: str
    database_url: str | None
    persistence: str
    artifact_limit_bytes: int = 5 * 1024 * 1024
    execution_timeout_seconds: int = 15

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.getenv("OMNI_ENV", "development").strip().lower() or "development"
        database_url = (os.getenv("DATABASE_URL") or "").strip() or None
        if env == "production" and not database_url:
            raise ConfigurationError("DATABASE_URL is required in production")
        return cls(
            env=env,
            database_url=database_url,
            persistence="postgres" if database_url else "memory",
        )


def build_store(settings: Settings):
    if settings.persistence == "postgres":
        from .postgres_store import PostgresStore

        if not settings.database_url:
            raise ConfigurationError("DATABASE_URL is required for postgres persistence")
        return PostgresStore(settings.database_url)

    if settings.env == "production":
        raise ConfigurationError("Production cannot use memory persistence")

    from .store import MemoryStore

    return MemoryStore()
