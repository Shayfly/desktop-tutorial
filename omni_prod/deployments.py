from __future__ import annotations
from dataclasses import dataclass
import re
import uuid

_ENV = re.compile(r"^[a-z][a-z0-9-]{0,31}$")

@dataclass(frozen=True)
class Promotion:
    deployment_id: str
    project_id: str
    version_id: str
    build_id: str
    environment: str
    artifact_key: str

def validate_environment(environment: str) -> str:
    if not _ENV.fullmatch(environment):
        raise ValueError("invalid deployment environment")
    return environment

def new_promotion(*, project_id: str, version_id: str, build_id: str,
                  environment: str, artifact_key: str) -> Promotion:
    validate_environment(environment)
    if not all([project_id, version_id, build_id, artifact_key]):
        raise ValueError("promotion fields must be non-empty")
    return Promotion(
        deployment_id=str(uuid.uuid4()),
        project_id=project_id,
        version_id=version_id,
        build_id=build_id,
        environment=environment,
        artifact_key=artifact_key,
    )

class PostgresDeploymentRepository:
    def __init__(self, database):
        self.database_url = database

    def promote(self, promotion: Promotion) -> None:
        from .db import transaction
        with transaction(self.database_url) as conn:
            with conn.cursor() as cur:
                # Retire only the currently active deployment in the same project/env.
                cur.execute(
                    """
                    UPDATE deployments
                    SET retired_at = NOW()
                    WHERE project_id = %s
                      AND environment = %s
                      AND retired_at IS NULL
                    """,
                    (promotion.project_id, promotion.environment),
                )
                cur.execute(
                    """
                    INSERT INTO deployments(
                        id, project_id, version_id, build_id,
                        environment, artifact_key
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        promotion.deployment_id,
                        promotion.project_id,
                        promotion.version_id,
                        promotion.build_id,
                        promotion.environment,
                        promotion.artifact_key,
                    ),
                )

    def current(self, *, project_id: str, environment: str):
        from .db import transaction
        validate_environment(environment)
        with transaction(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, version_id, build_id, artifact_key
                    FROM deployments
                    WHERE project_id = %s
                      AND environment = %s
                      AND retired_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (project_id, environment),
                )
                return cur.fetchone()
