from __future__ import annotations
from dataclasses import dataclass
import os

def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default

def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw else default

@dataclass(frozen=True)
class Settings:
    environment: str
    secret_key: str
    database_url: str
    redis_url: str
    s3_endpoint: str
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str
    sandbox_image: str
    sandbox_timeout_seconds: int
    sandbox_memory: str
    sandbox_cpus: str
    sandbox_pids: int
    db_pool_min_size: int
    db_pool_max_size: int
    db_pool_timeout_seconds: float
    db_connect_timeout_seconds: int
    redis_socket_timeout_seconds: float
    redis_connect_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.getenv("OMNI_ENV", "development")
        secret = _required("OMNI_SECRET_KEY")
        if env == "production" and len(secret) < 48:
            raise RuntimeError("OMNI_SECRET_KEY must be at least 48 chars in production")

        min_size = _int("OMNI_DB_POOL_MIN_SIZE", 2)
        max_size = _int("OMNI_DB_POOL_MAX_SIZE", 10)
        if min_size < 1 or max_size < min_size:
            raise RuntimeError("invalid database pool sizes")

        return cls(
            environment=env,
            secret_key=secret,
            database_url=_required("OMNI_DATABASE_URL"),
            redis_url=_required("OMNI_REDIS_URL"),
            s3_endpoint=_required("OMNI_S3_ENDPOINT"),
            s3_bucket=_required("OMNI_S3_BUCKET"),
            s3_access_key=_required("OMNI_S3_ACCESS_KEY"),
            s3_secret_key=_required("OMNI_S3_SECRET_KEY"),
            sandbox_image=os.getenv("OMNI_SANDBOX_IMAGE", "omni-sandbox:latest"),
            sandbox_timeout_seconds=_int("OMNI_SANDBOX_TIMEOUT_SECONDS", 180),
            sandbox_memory=os.getenv("OMNI_SANDBOX_MEMORY", "1024m"),
            sandbox_cpus=os.getenv("OMNI_SANDBOX_CPUS", "1.5"),
            sandbox_pids=_int("OMNI_SANDBOX_PIDS", 256),
            db_pool_min_size=min_size,
            db_pool_max_size=max_size,
            db_pool_timeout_seconds=_float("OMNI_DB_POOL_TIMEOUT_SECONDS", 10.0),
            db_connect_timeout_seconds=_int("OMNI_DB_CONNECT_TIMEOUT_SECONDS", 5),
            redis_socket_timeout_seconds=_float("OMNI_REDIS_SOCKET_TIMEOUT_SECONDS", 5.0),
            redis_connect_timeout_seconds=_float("OMNI_REDIS_CONNECT_TIMEOUT_SECONDS", 5.0),
        )
