from __future__ import annotations
from dataclasses import dataclass
from .config import Settings
from .db import DatabasePool
from .job_repository import PostgresBuildRepository
from .deployments import PostgresDeploymentRepository
from .storage import S3ArtifactStore
from .queueing import redis_connection

@dataclass
class ProductionAdapters:
    db_pool: DatabasePool
    builds: PostgresBuildRepository
    deployments: PostgresDeploymentRepository
    artifacts: S3ArtifactStore
    redis: object

    def close(self) -> None:
        self.db_pool.close()
        close = getattr(self.redis, "close", None)
        if callable(close):
            close()

def build_production_adapters(settings: Settings) -> ProductionAdapters:
    if settings.environment != "production":
        raise RuntimeError("production adapters require OMNI_ENV=production")

    pool = DatabasePool(
        settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        timeout_seconds=settings.db_pool_timeout_seconds,
        connect_timeout_seconds=settings.db_connect_timeout_seconds,
    )
    artifacts = S3ArtifactStore(
        endpoint=settings.s3_endpoint,
        bucket=settings.s3_bucket,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
    )
    redis = redis_connection(
        settings.redis_url,
        socket_timeout_seconds=settings.redis_socket_timeout_seconds,
        connect_timeout_seconds=settings.redis_connect_timeout_seconds,
    )
    return ProductionAdapters(
        db_pool=pool,
        builds=PostgresBuildRepository(pool),
        deployments=PostgresDeploymentRepository(pool),
        artifacts=artifacts,
        redis=redis,
    )

def assert_not_memory_adapter(obj: object) -> None:
    module = obj.__class__.__module__
    if module.endswith(".memory_adapters"):
        raise RuntimeError(
            f"memory adapter forbidden in production: {obj.__class__.__name__}"
        )
