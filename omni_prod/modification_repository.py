from __future__ import annotations
import json

from .evidence_json import dumps_evidence_for_terminal_state
from dataclasses import dataclass
from .product_spec import ProductSpec
from .spec_repository import SpecNotFound
from .workspace import SKIP_VERSION_CHECK, VersionConflict


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

    M4D.1: this pure function is the specification of that decision table,
    and its own tests pin it down independent of SQL/locking concerns. The
    LIVE `accept()` below does not call this function against a separately
    read `current_version_id` -- doing that (read current, decide, *then*
    write) is exactly the TOCTOU gap M4D.1 closed. Instead `accept()` passes
    `expected_source_version_id` straight to `workspace.commit(...,
    expected_current_version_id=...)`, which reads the real current version
    and compares atomically, under the same lock/transaction that would
    perform the insert, raising `VersionConflict` instead of ever returning
    an ill-gotten `current_version_id` for this function to reason about
    after the fact. The states below are still the real states `accept()`
    produces -- 'invalid_status' from its own status gate, 'conflict' from a
    caught `VersionConflict` (force=False), 'accept'/'accept_forced' from a
    successful `workspace.commit()` (force=False/True respectively) -- this
    function documents and regression-tests that mapping without being the
    thing that has to get the timing right.

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
                         repair_rounds, dumps_evidence_for_terminal_state(evidence_json or {}),
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

    def _mark_conflict(self, modification_id: str) -> None:
        """Bookkeeping only, run AFTER the merged promotion transaction in
        `accept()` has already rolled back on `VersionConflict` -- by the
        time this runs, `project_versions` is guaranteed untouched by this
        modification_id (see `accept()`), so there is no
        `promoted_version_id` to ever record for a conflict; it stays NULL."""
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE modification_requests SET status='CONFLICT' "
                        "WHERE id=%s AND status='READY_FOR_REVIEW'",
                        (modification_id,),
                    )

    def accept(self, modification_id: str, project_id: str, *, workspace, spec_repo,
               message: str = 'modification accepted', force: bool = False) -> dict:
        """Promotes a READY_FOR_REVIEW candidate to the project's current
        version. The candidate has never touched `project_versions` before
        this call (see `complete()`/migration 016); this is the first time
        its stored repository becomes a real, brand-new `ProjectVersion`,
        the same append-only way every other write path in this codebase
        produces a new version -- nothing is edited in place, and a
        rejected/conflicted modification never mutates `project_versions`
        at all.

        M4D.1 (production-blocking fix over the original M4 design): the
        entire promotion -- validating the ModificationRequest is still
        READY_FOR_REVIEW, reading its stored candidate, checking the
        candidate's source version against the project's REAL current
        version, inserting the new ProjectVersion, inserting its
        ProductSpec, and flipping the ModificationRequest to ACCEPTED -- now
        happens inside ONE database transaction, sharing a single cursor
        (`cur`) across `workspace.commit(cur=cur, ...)` and
        `spec_repo.save(cur=cur, ...)`. The expected-source-version check is
        `workspace.commit()`'s own atomic compare (see workspace.py's
        `VersionConflict`), performed under the SAME lock that would
        otherwise perform the INSERT -- so a conflict is detected and
        refused strictly BEFORE any row is written, never audited
        afterward. The original design called `workspace.commit()`
        unconditionally and only compared `new_version.parent_id` to the
        expected source *after* the row already existed in
        `project_versions` (and `current()` had therefore already silently
        advanced) -- a real, production-blocking bug: a caller could be
        told "conflict, not accepted" while the project's actual current
        version had already changed to the rejected candidate's content.
        That post-commit check is gone; `VersionConflict` is now the only
        way this method learns about a stale source, and by construction it
        can only be raised before the write.

        `force=True` passes `SKIP_VERSION_CHECK` to `workspace.commit()`
        instead of the real expected id, so the commit succeeds
        unconditionally on top of whatever is actually current -- the
        directive's explicit, controlled third option. `forced` in the
        return value reports whether this ended up mounting on top of a
        version other than the one the modification was proposed against
        (`new_version.parent_id != source_version_id`), which can only be
        true when `force=True`, since otherwise a mismatch always raises
        `VersionConflict` instead of succeeding.
        """
        try:
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
                        if status != 'READY_FOR_REVIEW':
                            return {'accepted': False, 'reason': 'invalid_status', 'status': status}

                        cur.execute(
                            "SELECT repository_json, spec_json FROM modification_candidates "
                            "WHERE modification_id = %s",
                            (modification_id,),
                        )
                        candidate_row = cur.fetchone()
                        if not candidate_row:
                            # Defensive only: complete() always writes
                            # modification_candidates in the same transaction
                            # as the READY_FOR_REVIEW status flip, so a
                            # READY_FOR_REVIEW row with no candidate should
                            # not happen.
                            raise RuntimeError(
                                f'modification {modification_id!r} is READY_FOR_REVIEW but has no stored candidate')
                        repository_json, spec_json = candidate_row
                        if isinstance(repository_json, str):
                            repository_json = json.loads(repository_json)
                        if isinstance(spec_json, str):
                            spec_json = json.loads(spec_json)

                        expected = SKIP_VERSION_CHECK if force else source_version_id
                        new_version = workspace.commit(
                            project_id=project_id, repository=repository_json, message=message,
                            expected_current_version_id=expected, cur=cur,
                        )

                        spec_repo.save(version_id=new_version.id, project_id=project_id,
                                       spec=ProductSpec.from_dict(spec_json), cur=cur)

                        cur.execute(
                            "UPDATE modification_requests SET status='ACCEPTED', accepted_at=now(), "
                            "promoted_version_id=%s WHERE id=%s",
                            (new_version.id, modification_id),
                        )
        except VersionConflict as exc:
            # Everything above rolled back with the transaction (real
            # Postgres: conn.transaction()'s __exit__ rolls back on
            # exception; this in-memory double never wrote anything to
            # begin with, since VersionConflict is raised before
            # bucket.append()). No INSERT, no spec row, no status change --
            # `current()` for this project is exactly what it was before
            # this call. Only now, in a fresh follow-up transaction, do we
            # record that this modification lost the race.
            self._mark_conflict(modification_id)
            return {'accepted': False, 'reason': 'conflict',
                    'current_version_id': exc.actual_current_version_id,
                    'source_version_id': exc.expected_current_version_id}

        forced = new_version.parent_id != source_version_id
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
        regenerate old code.' `workspace.restore()` (workspace.py) already
        does exactly that for the repository: it loads the named historical
        `ProjectVersion` and re-commits its *exact* stored repository as a
        new version -- nothing regenerated, no model call. This wraps it to
        also carry the historical `ProductSpec` forward, so the new version
        keeps M4B's ProjectVersion<->ProductSpec pairing. Raises KeyError
        (from workspace.get() inside restore()) if `target_version_id` is
        not a real version of this project -- a rollback target must be
        durable history, never invented.

        Rollback is an explicit, operator-directed override by design (like
        `accept(force=True)`) -- it does not pass an
        `expected_current_version_id`, so it always succeeds on top of
        whatever is actually current, the same as before M4D.1. What M4D.1
        adds here is consistency with `accept()`: the version commit and its
        spec save now share one transaction (`cur`), instead of two
        separate ones."""
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    new_version = workspace.restore(project_id=project_id, version_id=target_version_id,
                                                     message=message, cur=cur)
                    try:
                        spec = spec_repo.get(target_version_id, project_id)
                        spec_repo.save(version_id=new_version.id, project_id=project_id, spec=spec, cur=cur)
                        spec_restored = True
                    except SpecNotFound:
                        # A version committed before migration 016 / M4B (or
                        # one never produced by a modification) may have no
                        # spec row. Restoring its repository is still real
                        # and correct; the spec pairing is left unestablished
                        # for the new version too, matching the target -- not
                        # fabricated here.
                        spec_restored = False
        return {'version_id': new_version.id, 'restored_from': target_version_id, 'spec_restored': spec_restored}
