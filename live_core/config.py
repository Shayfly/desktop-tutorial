from __future__ import annotations

from dataclasses import dataclass
import os


class ConfigurationError(RuntimeError):
    """Raised when production configuration is unsafe or incomplete."""


# live_core reads only OMNI_DATABASE_URL, the same variable investor_app uses.
# DATABASE_URL is deliberately never read: on Vercel it predates the 25.10
# database switch and may point at a suspended database (decision #232, blocker 2).
DATABASE_ENV = "OMNI_DATABASE_URL"
# Memory persistence must be asked for by name. An unset OMNI_ENV is not
# treated as permission to run without a database.
MEMORY_OPT_IN_ENV = "OMNI_LIVE_PERSISTENCE"


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
        database_url = (os.getenv(DATABASE_ENV) or "").strip() or None
        if database_url:
            return cls(env=env, database_url=database_url, persistence="postgres")

        memory_requested = (os.getenv(MEMORY_OPT_IN_ENV) or "").strip().lower() == "memory"
        if memory_requested and env != "production":
            return cls(env=env, database_url=None, persistence="memory")

        raise ConfigurationError(
            f"{DATABASE_ENV} is required for live_core (DATABASE_URL is not read). "
            f"Memory persistence is allowed only outside production with {MEMORY_OPT_IN_ENV}=memory."
        )


def build_store(settings: Settings):
    if settings.persistence == "postgres":
        from .postgres_store import PostgresStore

        if not settings.database_url:
            raise ConfigurationError(f"{DATABASE_ENV} is required for postgres persistence")
        return PostgresStore(settings.database_url)

    if settings.env == "production":
        raise ConfigurationError("Production cannot use memory persistence")

    from .store import MemoryStore

    return MemoryStore()
