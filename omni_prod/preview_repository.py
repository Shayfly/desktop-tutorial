from __future__ import annotations
from datetime import datetime, timezone


class PostgresPreviewRepository:
    """Durable metadata for the M3 real-running-preview lifecycle.

    Deliberately mirrors the style of PostgresBuildRepository /
    PostgresSubscriptionService already in this codebase: constructed with a
    DatabasePool, each public method opens its own connection/transaction
    (no caller-supplied cursor needed here -- unlike the M1 build pipeline,
    nothing about creating/updating a preview row needs to commit atomically
    alongside another table).
    """

    def __init__(self, pool):
        self.pool = pool

    def create(self, preview_id: str, project_id: str, version_id: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError('ttl_seconds must be positive')
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    # now() + make_interval(secs => %s), not `%s || ' seconds'`::interval --
                    # the latter is `integer || text`, which Postgres rejects
                    # (concatenation needs text on both sides); caught before
                    # ever being run against a real database, not after.
                    cur.execute(
                        """
                        INSERT INTO project_previews(id, project_id, version_id, status, expires_at)
                        VALUES (%s, %s, %s, 'STARTING', now() + make_interval(secs => %s))
                        """,
                        (preview_id, project_id, version_id, ttl_seconds),
                    )

    def update_status(self, preview_id: str, status: str, url: str | None = None,
                       container_id: str | None = None, error: str | None = None) -> None:
        valid = {'STARTING', 'RUNNING', 'STOPPED', 'FAILED', 'EXPIRED'}
        if status not in valid:
            raise ValueError(f'invalid preview status: {status!r}')
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE project_previews
                        SET status = %s,
                            preview_url = COALESCE(%s, preview_url),
                            internal_container_id = COALESCE(%s, internal_container_id),
                            error_message = %s
                        WHERE id = %s
                        """,
                        (status, url, container_id, error, preview_id),
                    )

    def get(self, preview_id: str, project_id: str) -> dict:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, project_id, version_id, status, preview_url,
                           internal_container_id, error_message, created_at, expires_at
                    FROM project_previews
                    WHERE id = %s AND project_id = %s
                    """,
                    (preview_id, project_id),
                )
                row = cur.fetchone()
        if not row:
            raise KeyError('preview not found or access denied')
        return {
            'id': row[0], 'project_id': row[1], 'version_id': row[2], 'status': row[3],
            'preview_url': row[4], 'internal_container_id': row[5], 'error_message': row[6],
            'created_at': row[7].isoformat() if hasattr(row[7], 'isoformat') else str(row[7]),
            'expires_at': row[8].isoformat() if hasattr(row[8], 'isoformat') else str(row[8]),
        }

    def mark_expired(self) -> int:
        """Sweeps RUNNING previews past their TTL to EXPIRED. Returns the
        number of rows updated. Nothing in this session wires this to a
        scheduler -- see PATCH_APPLICATION_REPORT.md."""
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE project_previews
                        SET status = 'EXPIRED'
                        WHERE status = 'RUNNING' AND expires_at < now()
                        """
                    )
                    return cur.rowcount
