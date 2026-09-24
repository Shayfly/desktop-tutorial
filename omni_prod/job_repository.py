from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from .models import BuildStatus


@dataclass
class BuildJobDetails:
    build_id: str
    status: str
    phase: str
    message: str | None
    error_message: str | None
    repair_rounds: int
    result_version_id: str | None
    artifact_key: str | None
    # M1 blocker resolution: surfaced so API clients can see *which* gate
    # failed (verification / quality / security / rights) and the gate
    # evidence, not just a bare FAILED. Defaulted -> existing constructors
    # keep working.
    error_code: str | None = None
    evidence: dict | None = None


class PostgresBuildRepository:
    def __init__(self, database):
        # `database` may be a raw database_url string (legacy call sites) or a
        # DatabasePool instance (production_adapters.py / M1 durable pipeline).
        # `.db.transaction()` already handles both. The M1-added methods below
        # additionally accept an explicit cursor for cross-repository atomic
        # transactions and therefore require a DatabasePool specifically.
        self.database_url = database
        self.pool = database

    # ---- legacy, self-managed-transaction API -----------------------------
    # Preserved byte-for-byte: omni_prod/acceptance_pipeline.py calls
    # self.builds.create(build_id=..., project_id=..., version_id=...) with no
    # cursor, so this signature cannot change without breaking that caller
    # (and its test coverage). The M1 patch as pasted redefined create() to
    # require a leading `cur` positional argument, which would have broken
    # acceptance_pipeline.py with `TypeError: create() missing 1 required
    # positional argument: 'cur'`. The new cursor-taking variant is added
    # below instead, under a different name (create_with_cursor).

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
                   error_message: str | None = None,
                   result_version_id: str | None = None,
                   repair_rounds: int | None = None,
                   evidence_json: dict | None = None,
                   estimated_provider_cost_usd: float | None = None,
                   actual_provider_cost_usd: float | None = None) -> bool:
        """Extended in place (M1 Revision 2) with optional durable-evidence
        columns added by migration 013. All new parameters default to None/
        unset so existing callers (acceptance_pipeline.py) that only pass the
        original five keyword arguments are unaffected."""
        from .build_state import assert_transition
        from .db import transaction
        assert_transition(expected, target)

        started_sql = "started_at = COALESCE(started_at, NOW())," if target == BuildStatus.RUNNING else ""
        finished_sql = "finished_at = NOW()," if target in {
            BuildStatus.READY, BuildStatus.FAILED, BuildStatus.CANCELLED
        } else ""
        phase = target.value.upper()

        sql = f"""
            UPDATE build_jobs
            SET status = %s, phase = %s,
                {started_sql}
                {finished_sql}
                artifact_key = COALESCE(%s, artifact_key),
                error_code = %s,
                error_message = %s,
                result_version_id = COALESCE(%s, result_version_id),
                repair_rounds = COALESCE(%s, repair_rounds),
                evidence_json = COALESCE(%s::jsonb, evidence_json),
                estimated_provider_cost_usd = COALESCE(%s, estimated_provider_cost_usd),
                actual_provider_cost_usd = COALESCE(%s, actual_provider_cost_usd)
            WHERE id = %s AND status = %s
        """
        with transaction(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    target.value, phase, artifact_key, error_code, error_message,
                    result_version_id, repair_rounds,
                    json.dumps(evidence_json) if evidence_json is not None else None,
                    estimated_provider_cost_usd, actual_provider_cost_usd,
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

    # ---- M1 Revision 2: durable async pipeline additions -------------------
    # These participate in a caller-managed transaction (a single
    # `with pool.connection() as conn: with conn.transaction(): with
    # conn.cursor() as cur:` block in investor_app.py) so that the credit
    # reservation, build request, build job and outbox row commit atomically.

    def create_request(self, cur, *, build_id: str, user_id: str, internal_project_id: str, prompt: str,
                        target_markets: tuple, branding_visible: bool | None, white_label_name: str | None,
                        rights_evidence: list, public_project_id: str | None = None) -> None:
        # public_project_id (migration 015): the worker's branding/provenance
        # step embeds the user-facing project id, which the internal tenant
        # key does not reveal. Optional keyword -> old call sites unaffected.
        cur.execute(
            "INSERT INTO build_requests(build_id, user_id, internal_project_id, prompt, target_markets, branding_visible, white_label_name, rights_evidence, public_project_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)",
            (build_id, user_id, internal_project_id, prompt, json.dumps(list(target_markets)), branding_visible, white_label_name, json.dumps(rights_evidence), public_project_id)
        )

    def get_request(self, build_id: str) -> dict:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, internal_project_id, prompt, target_markets, branding_visible, white_label_name, rights_evidence, public_project_id FROM build_requests WHERE build_id = %s", (build_id,))
                row = cur.fetchone()
                if not row: raise KeyError("Build request not found")
                return {"user_id": row[0], "internal_project_id": row[1], "prompt": row[2], "target_markets": tuple(row[3]), "branding_visible": row[4], "white_label_name": row[5], "rights_evidence": row[6], "public_project_id": row[7]}

    def create_with_cursor(self, cur, *, build_id: str, project_id: str, version_id: str) -> None:
        """Renamed from the pasted patch's create(cur, ...) to avoid colliding
        with the pre-existing, still-in-use create() above."""
        cur.execute(
            "INSERT INTO build_jobs(id, project_id, version_id, status, phase) VALUES (%s, %s, %s, %s, %s)",
            (build_id, project_id, version_id, BuildStatus.QUEUED.value, 'QUEUED')
        )

    def create_outbox(self, cur, *, build_id: str) -> None:
        cur.execute("INSERT INTO build_outbox(build_id) VALUES (%s)", (build_id,))

    def mark_outbox_enqueued(self, build_id: str) -> None:
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("UPDATE build_outbox SET enqueued_at = now() WHERE build_id = %s", (build_id,))

    def dispatch_pending_outbox(self, enqueue, *, older_than_seconds: int = 30, limit: int = 100) -> list[str]:
        """Transactional-outbox relay (M1 blocker resolution).

        The API commits reservation + request + job + outbox row atomically,
        *then* enqueues to Redis. If Redis is down at that moment the build is
        durably accepted but was never dispatched, and before this method
        nothing ever retried it: the credits stayed RESERVED and the job sat
        at QUEUED forever. This re-dispatches such rows, one per transaction,
        with FOR UPDATE SKIP LOCKED so concurrent relays never double-claim a
        row. `older_than_seconds` leaves rows the API is still in the middle
        of enqueueing alone. Duplicate delivery (enqueue succeeded, commit
        failed) is safe: the worker's QUEUED->RUNNING transition is
        conditional, so a second delivery is a no-op."""
        dispatched: list[str] = []
        for _ in range(max(0, int(limit))):
            with self.pool.connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT build_id FROM build_outbox
                            WHERE enqueued_at IS NULL
                              AND created_at < now() - make_interval(secs => %s)
                            ORDER BY id
                            LIMIT 1
                            FOR UPDATE SKIP LOCKED
                            """,
                            (int(older_than_seconds),),
                        )
                        row = cur.fetchone()
                        if not row:
                            return dispatched
                        build_id = row[0]
                        enqueue(build_id)  # raises -> transaction rolls back, row stays pending
                        cur.execute("UPDATE build_outbox SET enqueued_at = now() WHERE build_id = %s", (build_id,))
            dispatched.append(build_id)
        return dispatched

    def update_phase(self, build_id: str, phase: str, message: str = "") -> None:
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("UPDATE build_jobs SET phase = %s, message = %s WHERE id = %s", (phase, message, build_id))

    def get_details(self, build_id: str, internal_project_id: str) -> BuildJobDetails:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT status, phase, message, error_message, repair_rounds, result_version_id, artifact_key, error_code, evidence_json FROM build_jobs WHERE id = %s AND project_id = %s", (build_id, internal_project_id))
                row = cur.fetchone()
                if not row: raise KeyError("Job not found or access denied")
                return BuildJobDetails(build_id=build_id, status=row[0], phase=row[1], message=row[2], error_message=row[3], repair_rounds=row[4], result_version_id=row[5], artifact_key=row[6], error_code=row[7], evidence=row[8])
