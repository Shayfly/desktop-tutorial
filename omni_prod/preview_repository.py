from __future__ import annotations


def _iso(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, 'isoformat') else str(value)


class PostgresPreviewRepository:
    """Durable metadata for the M3 real-running-preview lifecycle.

    STARTING -> RUNNING | FAILED | NOT_PREVIEWABLE | STOPPED
    RUNNING  -> STOPPED | EXPIRED
    EXPIRED  -> STOPPED   (container cleanup after TTL)

    M3 Revision 2: every write the *launch* task makes is conditional on
    `status = 'STARTING'`. A DELETE can land while the worker is still
    starting or health-probing the container; without the condition the
    worker's later write would silently flip a user-stopped preview back to
    RUNNING (or FAILED). Each method returns whether it actually applied, so
    the worker knows to tear down a container nobody wants any more.

    The unconditional `update_status()` from M3 draft 1 is removed for that
    reason -- it had no callers outside worker_tasks.py and the M3 tests.
    """

    STOPPABLE = ('STARTING', 'RUNNING', 'EXPIRED')

    def __init__(self, pool):
        self.pool = pool

    def create(self, preview_id: str, project_id: str, version_id: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError('ttl_seconds must be positive')
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    # make_interval(secs => %s), not `%s || ' seconds'`::interval
                    # (integer || text is not a valid Postgres operator).
                    cur.execute(
                        """
                        INSERT INTO project_previews(id, project_id, version_id, status, expires_at)
                        VALUES (%s, %s, %s, 'STARTING', now() + make_interval(secs => %s))
                        """,
                        (preview_id, project_id, version_id, ttl_seconds),
                    )

    def _conditional_update(self, sql: str, params: tuple) -> bool:
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    return cur.rowcount == 1

    def record_runtime(self, preview_id: str, *, container_id: str, runtime_host: str,
                       host_port: int, workdir: str) -> bool:
        """Persisted immediately after `docker run`, before the health probe,
        so a stop request during probing can find (and clean up) the
        container. Still STARTING -- RUNNING only after the probe passes."""
        return self._conditional_update(
            """
            UPDATE project_previews
            SET internal_container_id = %s, runtime_host = %s, host_port = %s, workdir_path = %s
            WHERE id = %s AND status = 'STARTING'
            """,
            (container_id, runtime_host, host_port, workdir, preview_id),
        )

    def mark_running(self, preview_id: str, *, url: str) -> bool:
        return self._conditional_update(
            """
            UPDATE project_previews
            SET status = 'RUNNING', preview_url = %s, error_message = NULL
            WHERE id = %s AND status = 'STARTING'
            """,
            (url, preview_id),
        )

    def mark_failed(self, preview_id: str, *, error: str, status: str = 'FAILED') -> bool:
        if status not in {'FAILED', 'NOT_PREVIEWABLE'}:
            raise ValueError(f'invalid failure status: {status!r}')
        return self._conditional_update(
            """
            UPDATE project_previews
            SET status = %s, error_message = %s
            WHERE id = %s AND status = 'STARTING'
            """,
            (status, error[:4000], preview_id),
        )

    def request_stop(self, preview_id: str, project_id: str) -> dict:
        """User-initiated stop. Raises KeyError if the preview does not exist
        for this project. Idempotent: an already-terminal preview is returned
        unchanged (`changed=False`). `needs_cleanup` is True whenever the row
        is STOPPED but the stop task has not yet confirmed cleanup, so a
        retried DELETE re-dispatches a cleanup that previously failed to
        enqueue."""
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT status, runtime_host, cleaned_at
                        FROM project_previews
                        WHERE id = %s AND project_id = %s
                        FOR UPDATE
                        """,
                        (preview_id, project_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise KeyError('preview not found or access denied')
                    status, runtime_host, cleaned_at = row[0], row[1], row[2]
                    changed = status in self.STOPPABLE
                    if changed:
                        cur.execute(
                            """
                            UPDATE project_previews
                            SET status = 'STOPPED', stopped_at = now()
                            WHERE id = %s
                            """,
                            (preview_id,),
                        )
                        status = 'STOPPED'
        return {
            'status': status,
            'changed': changed,
            'runtime_host': runtime_host,
            'needs_cleanup': status == 'STOPPED' and cleaned_at is None,
        }

    def get(self, preview_id: str, project_id: str) -> dict:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, project_id, version_id, status, preview_url,
                           internal_container_id, error_message, created_at, expires_at,
                           runtime_host, host_port, workdir_path, stopped_at, cleaned_at
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
            'created_at': _iso(row[7]), 'expires_at': _iso(row[8]),
            'runtime_host': row[9], 'host_port': row[10], 'workdir_path': row[11],
            'stopped_at': _iso(row[12]), 'cleaned_at': _iso(row[13]),
        }

    def get_runtime(self, preview_id: str) -> dict | None:
        """Internal (worker-side) lookup, not tenant-scoped: the stop task
        only ever receives a preview_id the API already authorized."""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT status, internal_container_id, runtime_host, workdir_path, cleaned_at
                    FROM project_previews WHERE id = %s
                    """,
                    (preview_id,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return {'status': row[0], 'container_id': row[1], 'runtime_host': row[2],
                'workdir': row[3], 'cleaned_at': _iso(row[4])}

    def mark_cleaned(self, preview_id: str) -> None:
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("UPDATE project_previews SET cleaned_at = now() WHERE id = %s", (preview_id,))

    def mark_crashed(self, preview_id: str, error: str) -> bool:
        """A preview can pass startup health and then die during behavioral
        acceptance. Keep preview runtime state independent from acceptance
        readiness, but reflect an actually-dead RUNNING container truthfully.
        """
        return self._conditional_update(
            """
            UPDATE project_previews
            SET status = 'FAILED', error_message = %s
            WHERE id = %s AND status = 'RUNNING'
            """,
            (str(error)[:4000], preview_id),
        )

    def _build_for_version(self, cur, project_id: str, version_id: str, *, for_update: bool = False):
        lock = ' FOR UPDATE' if for_update else ''
        cur.execute(
            """
            SELECT id, evidence_json
            FROM build_jobs
            WHERE project_id = %s AND (result_version_id = %s OR version_id = %s)
            ORDER BY CASE WHEN result_version_id = %s THEN 0 ELSE 1 END,
                     finished_at DESC NULLS LAST, created_at DESC
            LIMIT 1
            """ + lock,
            (project_id, version_id, version_id, version_id),
        )
        return cur.fetchone()

    def record_acceptance(self, preview_id: str, project_id: str, version_id: str, report) -> str | None:
        """Persist acceptance evidence in the owning build's durable JSON.

        This avoids a parallel evidence store and keeps Task 11 compatible
        with the current schema: build/version/preview identifiers are all
        embedded in the evidence object and the owning build row is locked
        while jsonb_set writes the report. Legacy versions with no build row
        return None and therefore remain release-ineligible.
        """
        from .evidence_json import dumps_evidence
        payload = report.to_dict() if hasattr(report, 'to_dict') else dict(report)
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    row = self._build_for_version(cur, project_id, version_id, for_update=True)
                    if not row:
                        return None
                    build_id = row[0]
                    payload = dict(payload)
                    payload.update({
                        'build_id': build_id, 'preview_id': preview_id,
                        'project_id': project_id, 'version_id': version_id,
                    })
                    cur.execute(
                        """
                        UPDATE build_jobs
                        SET evidence_json = jsonb_set(
                            jsonb_set(
                                COALESCE(evidence_json, '{}'::jsonb),
                                '{web_saas_acceptance_reports}',
                                COALESCE(evidence_json->'web_saas_acceptance_reports', '{}'::jsonb)
                                    || jsonb_build_object(%s, %s::jsonb),
                                true
                            ),
                            '{web_saas_acceptance_latest_preview_id}',
                            to_jsonb(%s::text),
                            true
                        )
                        WHERE id = %s
                        """,
                        (preview_id, dumps_evidence(payload), preview_id, build_id),
                    )
                    return build_id

    def get_acceptance(self, project_id: str, version_id: str, preview_id: str | None = None) -> dict | None:
        import json
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                row = self._build_for_version(cur, project_id, version_id)
        if not row:
            return None
        evidence = row[1] or {}
        if isinstance(evidence, str):
            evidence = json.loads(evidence)
        if not isinstance(evidence, dict):
            return None
        reports = evidence.get('web_saas_acceptance_reports') or {}
        if not isinstance(reports, dict):
            return None
        wanted = preview_id or evidence.get('web_saas_acceptance_latest_preview_id')
        result = reports.get(wanted) if wanted else None
        return dict(result) if isinstance(result, dict) else None

    def release_eligible(self, preview_id: str, project_id: str) -> bool:
        preview = self.get(preview_id, project_id)
        if preview['status'] != 'RUNNING':
            return False
        acceptance = self.get_acceptance(project_id, preview['version_id'], preview_id)
        return bool(acceptance and acceptance.get('status') == 'PASS' and acceptance.get('release_eligible') is True)

    def get_route(self, preview_id: str) -> tuple[str, int] | None:
        """For the external routing layer that serves PREVIEW_DOMAIN_TEMPLATE:
        maps a preview id to its upstream (runtime_host, host_port), only
        while RUNNING and unexpired. The router itself is infrastructure
        outside this repository (see PATCH_APPLICATION_REPORT.md)."""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT runtime_host, host_port FROM project_previews
                    WHERE id = %s AND status = 'RUNNING' AND expires_at > now()
                      AND runtime_host IS NOT NULL AND host_port IS NOT NULL
                    """,
                    (preview_id,),
                )
                row = cur.fetchone()
        return (row[0], int(row[1])) if row else None

    def mark_expired(self) -> int:
        """Sweeps RUNNING previews past their TTL to EXPIRED. Returns the
        number of rows updated. Nothing in this repository schedules it and
        it does not stop containers -- see PATCH_APPLICATION_REPORT.md."""
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
