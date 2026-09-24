from __future__ import annotations
import json
from dataclasses import dataclass
from .product_spec import ProductSpec
from .spec_repository import SpecNotFound


def _iso(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, 'isoformat') else str(value)


_TERMINAL_COMPLETION_STATUSES = {'NEEDS_CLARIFICATION', 'READY_FOR_REVIEW', 'FAILED'}
_REJECTABLE_STATUSES = {'READY_FOR_REVIEW', 'FAILED', 'NEEDS_CLARIFICATION', 'CONFLICT'}


def resolve_accept(*, status: str, expected_source_version_id: str,
                    current_version_id: str | None, force: bool) -> str:
    """M4's CONCURRENCY REQUIREMENT, decoupled from SQL so it is directly
    unit-testable: Version 10 is current; Modification A and Modification B
    both start from V10; A is accepted first (current becomes V11); B
    finishes and tries to accept -- B's `expected_source_version_id` (V10) no
    longer equals `current_version_id` (V11), so B must not silently become
    the new current version and overwrite what A did.

    Returns one of:
      'invalid_status'  -- not READY_FOR_REVIEW; nothing to accept.
      'conflict'        -- current version moved since this modification was
                           proposed, and `force` was not set. Per the
                           directive's own options, the caller can leave this
                           as an explicit alternate candidate (the default --
                           re-run `CandidateModificationEngine.propose()`
                           against the new current version for a rebase), or
                           retry with `force=True`.
      'accept'          -- current version still matches source_version_id;
                           safe to promote normally.
      'accept_forced'   -- current version had moved, but `force=True` was an
                           explicit, controlled decision to override it
                           anyway (the directive's third option).
    """
    if status != 'READY_FOR_REVIEW':
        return 'invalid_status'
    if current_version_id != expected_source_version_id:
        return 'accept_forced' if force else 'conflict'
    return 'accept'


@dataclass
class ModificationDetails:
    id: str
    status: str
    classification: str | None
    classification_reason: str | None
    billable: bool | None
    source_version_id: str
    promoted_version_id: str | None
    repair_rounds: int
    evidence: dict | None
    error_code: str | None
    error_message: str | None
    created_at: str | None
    started_at: str | None
    completed_at: str | None
    accepted_at: str | None
    rejected_at: str | None


class PostgresModificationRepository:
    """M4A: durable `ModificationRequest` lifecycle, plus M4D's accept/
    reject/rollback. Structure mirrors job_repository.PostgresBuildRepository
    exactly -- create()/create_outbox()/mark_outbox_enqueued()/
    dispatch_pending_outbox() are the same transactional-outbox shape M1
    already established for builds, applied to `modification_requests` /
    `modification_outbox` (migration 016) instead of `build_jobs` /
    `build_outbox`; nothing here reuses M1's tables directly.
    """

    def __init__(self, pool):
        self.pool = pool

    # ---- creation / outbox (participate in a caller-managed transaction,
    # exactly like job_repository.create_with_cursor/create_outbox) ---------

    def create(self, cur, *, modification_id: str, project_id: str, user_id: str,
               source_version_id: str, followup: str,
               target_markets: tuple[str, ...] = ('US', 'EU', 'IL'),
               rights_evidence: list[dict] | tuple[dict, ...] = ()) -> None:
        """`target_markets`/`rights_evidence` are captured here, durably, the
        same way `job_repository.create_request()` captures them for a build
        -- so the worker (a separate process) never has to fall back to
        in-memory API-process state for the M4E rights/provenance gate."""
        cur.execute(
            "INSERT INTO modification_requests"
            "(id, project_id, user_id, source_version_id, source_spec_version_id, followup, "
            "target_markets_json, rights_evidence_json, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, 'QUEUED')",
            (modification_id, project_id, user_id, source_version_id, source_version_id, followup,
             json.dumps(list(target_markets)), json.dumps(list(rights_evidence))),
        )

    def create_outbox(self, cur, *, modification_id: str) -> None:
        cur.execute("INSERT INTO modification_outbox(modification_id) VALUES (%s)", (modification_id,))

    def mark_outbox_enqueued(self, modification_id: str) -> None:
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE modification_outbox SET enqueued_at = now() WHERE modification_id = %s",
                        (modification_id,),
                    )

    def dispatch_pending_outbox(self, enqueue, *, older_than_seconds: int = 30, limit: int = 100) -> list[str]:
        """Identical relay logic to job_repository.dispatch_pending_outbox()
        (one row per transaction, FOR UPDATE SKIP LOCKED, duplicate delivery
        safe because transition_running() below is conditional) -- see that
        method's docstring for the full rationale, unchanged here."""
        dispatched: list[str] = []
        for _ in range(max(0, int(limit))):
            with self.pool.connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT modification_id FROM modification_outbox
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
                        modification_id = row[0]
                        enqueue(modification_id)  # raises -> transaction rolls back, row stays pending
                        cur.execute(
                            "UPDATE modification_outbox SET enqueued_at = now() WHERE modification_id = %s",
                            (modification_id,),
                        )
            dispatched.append(modification_id)
        return dispatched

    # ---- worker-side: load the durable request, drive it to completion ----

    def get_request(self, modification_id: str) -> dict:
        """Internal (worker-side) lookup, not tenant-scoped -- the worker
        only ever receives a modification_id the API already authorized when
        it created the row, the same convention preview_repository.py's
        get_runtime() documents for the same reason."""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT project_id, user_id, source_version_id, followup, "
                    "target_markets_json, rights_evidence_json "
                    "FROM modification_requests WHERE id = %s",
                    (modification_id,),
                )
                row = cur.fetchone()
        if not row:
            raise KeyError('modification request not found')
        target_markets, rights_evidence = row[4], row[5]
        if isinstance(target_markets, str):
            target_markets = json.loads(target_markets)
        if isinstance(rights_evidence, str):
            rights_evidence = json.loads(rights_evidence)
        return {'project_id': row[0], 'user_id': row[1], 'source_version_id': row[2], 'followup': row[3],
                'target_markets': tuple(target_markets or ('US', 'EU', 'IL')),
                'rights_evidence': list(rights_evidence or [])}

    def transition_running(self, modification_id: str) -> bool:
        """QUEUED -> RUNNING, conditional so a duplicate outbox/queue
        delivery is a no-op (acceptance test T: idempotent retry)."""
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE modification_requests SET status='RUNNING', started_at=now() "
                        "WHERE id=%s AND status='QUEUED'",
                        (modification_id,),
                    )
                    return cur.rowcount == 1

    def complete(self, modification_id: str, *, project_id: str, status: str,
                 classification: str | None = None, classification_reason: str | None = None,
                 billable: bool | None = None,
                 candidate_repository: dict[str, str] | None = None,
                 candidate_spec: ProductSpec | None = None,
                 repair_rounds: int = 0, evidence_json: dict | None = None,
                 error_code: str | None = None, error_message: str | None = None) -> bool:
        """RUNNING -> one of NEEDS_CLARIFICATION / READY_FOR_REVIEW / FAILED,
        conditional on RUNNING so a duplicate delivery after completion is a
        no-op. Used for both the normal outcome path and the exception path
        (worker catches the exception, calls this with status='FAILED').

        For READY_FOR_REVIEW, `candidate_repository`/`candidate_spec` are
        required and are written to `modification_candidates` in the *same*
        transaction as the status flip -- the candidate is deliberately never
        committed to `project_versions` here (see migration 016's comment on
        `modification_requests`): only `accept()` promotes it to a real,
        current-advancing version, which is what keeps the concurrency
        scenario in `resolve_accept()` correct."""
        if status not in _TERMINAL_COMPLETION_STATUSES:
            raise ValueError(f'invalid completion status: {status!r}')
        if status == 'READY_FOR_REVIEW' and (candidate_repository is None or candidate_spec is None):
            raise ValueError('READY_FOR_REVIEW completion requires candidate_repository and candidate_spec')
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE modification_requests
                        SET status = %s, completed_at = now(),
                            classification = %s, classification_reason = %s, billable = %s,
                            repair_rounds = %s, evidence_json = %s::jsonb,
                            error_code = %s, error_message = %s
                        WHERE id = %s AND status = 'RUNNING'
                        """,
                        (status, classification, classification_reason, billable,
                         repair_rounds, json.dumps(evidence_json or {}),
                         error_code, error_message, modification_id),
                    )
                    applied = cur.rowcount == 1
                    if applied and status == 'READY_FOR_REVIEW':
                        cur.execute(
                            "INSERT INTO modification_candidates"
                            "(modification_id, project_id, repository_json, spec_json) "
                            "VALUES (%s, %s, %s::jsonb, %s::jsonb) "
                            "ON CONFLICT (modification_id) DO NOTHING",
                            (modification_id, project_id, json.dumps(candidate_repository),
                             json.dumps(candidate_spec.to_dict())),
                        )
                    return applied

    # ---- read ---------------------------------------------------------

    def get_details(self, modification_id: str, project_id: str) -> ModificationDetails:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT status, classification, classification_reason, billable,
                           source_version_id, promoted_version_id, repair_rounds, evidence_json,
                           error_code, error_message,
                           created_at, started_at, completed_at, accepted_at, rejected_at
                    FROM modification_requests WHERE id = %s AND project_id = %s
                    """,
                    (modification_id, project_id),
                )
                row = cur.fetchone()
        if not row:
            raise KeyError('modification not found or access denied')
        return ModificationDetails(
            id=modification_id, status=row[0], classification=row[1], classification_reason=row[2],
            billable=row[3], source_version_id=row[4], promoted_version_id=row[5], repair_rounds=row[6],
            evidence=row[7], error_code=row[8], error_message=row[9],
            created_at=_iso(row[10]), started_at=_iso(row[11]), completed_at=_iso(row[12]),
            accepted_at=_iso(row[13]), rejected_at=_iso(row[14]),
        )

    def get_candidate(self, modification_id: str, project_id: str) -> dict:
        """Tenant-scoped read of the pending candidate stored by `complete()`
        for a READY_FOR_REVIEW modification -- used both by a review UI and
        by `accept()` itself. Raises KeyError if this modification has no
        stored candidate (wrong status, or access denied)."""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT repository_json, spec_json FROM modification_candidates "
                    "WHERE modification_id = %s AND project_id = %s",
                    (modification_id, project_id),
                )
                row = cur.fetchone()
        if not row:
            raise KeyError('no candidate stored for this modification, or access denied')
        repository_json, spec_json = row
        if isinstance(repository_json, str):
            repository_json = json.loads(repository_json)
        if isinstance(spec_json, str):
            spec_json = json.loads(spec_json)
        return {'repository': repository_json, 'spec': ProductSpec.from_dict(spec_json)}

    # ---- M4D: accept / reject / rollback -----------------------------

    def _mark_conflict(self, modification_id: str, *, promoted_version_id: str | None = None) -> None:
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE modification_requests "
                        "SET status='CONFLICT', promoted_version_id=COALESCE(%s, promoted_version_id) "
                        "WHERE id=%s AND status='READY_FOR_REVIEW'",
                        (promoted_version_id, modification_id),
                    )

    def accept(self, modification_id: str, project_id: str, *, workspace, spec_repo,
               message: str = 'modification accepted', force: bool = False) -> dict:
        """Promotes a READY_FOR_REVIEW candidate to the project's current
        version. The candidate has never touched `project_versions` before
        this call (see `complete()`/migration 016); this is the first time
        its stored repository becomes a real, brand-new `ProjectVersion` (via
        the existing, unmodified `workspace.commit()`), the same append-only
        way every other write path in this codebase produces a new version --
        nothing is edited in place, and a rejected/conflicted modification
        never mutates `project_versions` at all.

        Concurrency (M4's CONCURRENCY REQUIREMENT): see `resolve_accept()`.
        The row lock taken below (over both `modification_requests` and the
        `modification_candidates` read) is released before
        `workspace.commit()` is called -- holding it across that call would
        buy nothing (it does not lock `project_versions`) while risking pool
        exhaustion, since `workspace.commit()` opens its own connection from
        the same pool. The real serialization against a *concurrent accept on
        the same project* happens inside `workspace.commit()` itself, via its
        own `pg_advisory_xact_lock` keyed by project_id
        (`workspace.PostgresProjectWorkspace.commit()`). This method's own
        job is (a) the READY_FOR_REVIEW / stale-source pre-check, done under
        a row lock so two concurrent accept() calls for the *same*
        modification_id can't both proceed, and (b) a post-commit check of
        `new_version.parent_id` -- the ground truth of what was actually
        current at commit time -- to catch the rare window where a *second*
        modification's accept() raced through its own pre-check between this
        call's pre-check and its commit. On that rare race, the commit
        already happened (an extra, valid-but-unlinked version now exists in
        history); this is reported as `conflict_detected_at_commit` rather
        than silently marked ACCEPTED, and never promoted onto
        `promoted_version_id` as this modification's success.
        """
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT source_version_id, status FROM modification_requests "
                        "WHERE id = %s AND project_id = %s FOR UPDATE",
                        (modification_id, project_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise KeyError('modification not found or access denied')
                    source_version_id, status = row
                    candidate_row = None
                    if status == 'READY_FOR_REVIEW':
                        cur.execute(
                            "SELECT repository_json, spec_json FROM modification_candidates "
                            "WHERE modification_id = %s",
                            (modification_id,),
                        )
                        candidate_row = cur.fetchone()

        if status != 'READY_FOR_REVIEW':
            return {'accepted': False, 'reason': 'invalid_status', 'status': status}
        if not candidate_row:
            # Defensive only: complete() always writes modification_candidates
            # in the same transaction as the READY_FOR_REVIEW status flip, so
            # a READY_FOR_REVIEW row with no candidate should not happen.
            raise RuntimeError(f'modification {modification_id!r} is READY_FOR_REVIEW but has no stored candidate')
        repository_json, spec_json = candidate_row
        if isinstance(repository_json, str):
            repository_json = json.loads(repository_json)
        if isinstance(spec_json, str):
            spec_json = json.loads(spec_json)

        current = workspace.current(project_id=project_id)
        current_version_id = current.id if current is not None else None
        decision = resolve_accept(status=status, expected_source_version_id=source_version_id,
                                  current_version_id=current_version_id, force=force)
        if decision == 'conflict':
            self._mark_conflict(modification_id)
            return {'accepted': False, 'reason': 'conflict',
                    'current_version_id': current_version_id, 'source_version_id': source_version_id}

        new_version = workspace.commit(project_id=project_id, repository=repository_json, message=message)

        if new_version.parent_id != source_version_id and not force:
            self._mark_conflict(modification_id, promoted_version_id=new_version.id)
            return {'accepted': False, 'reason': 'conflict_detected_at_commit',
                    'orphaned_version_id': new_version.id, 'source_version_id': source_version_id}

        spec_repo.save(version_id=new_version.id, project_id=project_id, spec=ProductSpec.from_dict(spec_json))

        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE modification_requests SET status='ACCEPTED', accepted_at=now(), "
                        "promoted_version_id=%s WHERE id=%s",
                        (new_version.id, modification_id),
                    )
        # `forced` reports whether this accept only succeeded because `force`
        # overrode a stale source -- either detected up front (decision ==
        # 'accept_forced') or only discovered belatedly by the post-commit
        # check above (new_version.parent_id != source_version_id, force=True).
        # Checking both keeps this field accurate for the rare commit-time race.
        forced = decision == 'accept_forced' or new_version.parent_id != source_version_id
        return {'accepted': True, 'new_version_id': new_version.id, 'forced': forced}

    def reject(self, modification_id: str, project_id: str, *, reason: str = '') -> dict:
        """Leaves the current accepted version untouched by construction --
        this never writes to project_versions."""
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT status FROM modification_requests WHERE id=%s AND project_id=%s FOR UPDATE",
                        (modification_id, project_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise KeyError('modification not found or access denied')
                    status = row[0]
                    if status not in _REJECTABLE_STATUSES:
                        return {'rejected': False, 'status': status}
                    cur.execute(
                        "UPDATE modification_requests SET status='REJECTED', rejected_at=now(), "
                        "error_message=COALESCE(%s, error_message) WHERE id=%s",
                        (reason or None, modification_id),
                    )
        return {'rejected': True}

    def rollback(self, project_id: str, *, target_version_id: str, workspace, spec_repo,
                 message: str = 'rollback') -> dict:
        """M4D: 'Rollback must reference durable historical versions, not
        regenerate old code.' `workspace.restore()` (workspace.py,
        unmodified) already does exactly that for the repository: it loads
        the named historical `ProjectVersion` and re-commits its *exact*
        stored repository as a new version -- nothing regenerated, no model
        call. This wraps it to also carry the historical `ProductSpec`
        forward, so the new version keeps M4B's ProjectVersion<->ProductSpec
        pairing. Raises KeyError (from workspace.get() inside restore()) if
        `target_version_id` is not a real version of this project -- a
        rollback target must be durable history, never invented."""
        new_version = workspace.restore(project_id=project_id, version_id=target_version_id, message=message)
        try:
            spec = spec_repo.get(target_version_id, project_id)
            spec_repo.save(version_id=new_version.id, project_id=project_id, spec=spec)
            spec_restored = True
        except SpecNotFound:
            # A version committed before migration 016 / M4B (or one never
            # produced by a modification) may have no spec row. Restoring its
            # repository is still real and correct; the spec pairing is left
            # unestablished for the new version too, matching the target --
            # not fabricated here.
            spec_restored = False
        return {'version_id': new_version.id, 'restored_from': target_version_id, 'spec_restored': spec_restored}
