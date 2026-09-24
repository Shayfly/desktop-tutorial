from __future__ import annotations
from dataclasses import asdict
from .models import BuildStatus

class PostgresBuildRepository:
    def __init__(self, database):
        self.database_url = database

    def create(self, *, build_id: str, project_id: str, version_id: str) -> None:
        from .db import transaction
        with transaction(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO build_jobs(id, project_id, version_id, status)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (build_id, project_id, version_id, BuildStatus.QUEUED.value),
                )

    def transition(self, *, build_id: str, expected: BuildStatus, target: BuildStatus,
                   artifact_key: str | None = None,
                   error_code: str | None = None,
                   error_message: str | None = None) -> bool:
        from .build_state import assert_transition
        from .db import transaction
        assert_transition(expected, target)

        started_sql = "started_at = COALESCE(started_at, NOW())," if target == BuildStatus.RUNNING else ""
        finished_sql = "finished_at = NOW()," if target in {
            BuildStatus.READY, BuildStatus.FAILED, BuildStatus.CANCELLED
        } else ""

        sql = f"""
            UPDATE build_jobs
            SET status = %s,
                {started_sql}
                {finished_sql}
                artifact_key = COALESCE(%s, artifact_key),
                error_code = %s,
                error_message = %s
            WHERE id = %s AND status = %s
        """
        with transaction(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    target.value, artifact_key, error_code, error_message,
                    build_id, expected.value
                ))
                return cur.rowcount == 1

    def get_status(self, build_id: str) -> BuildStatus | None:
        from .db import transaction
        with transaction(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT status FROM build_jobs WHERE id = %s", (build_id,))
                row = cur.fetchone()
                return BuildStatus(row[0]) if row else None
