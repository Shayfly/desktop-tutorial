"""The direction sketches table (migration 049): one row per sketch shown to a customer (S6.3, slice 2).

The table holds no amount. The money of a model call is in intake_reservations (this row points at it); the credits of a
further sketch are in credit_reservations (slice 5), keyed by the sketch id. Every read names its project AND account:
a sketch id of another project or account is the same answer as an id that never existed (None).

A database without migration 049 raises SketchStoreMissing, never an empty result: the routes answer 503 with the
migration's name (fail closed)."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

FUNDING = ('none', 'company_first', 'owner', 'customer')
COPY_STATES = ('none', 'pending', 'written', 'failed')
_COLS = ('id, project_id, account_id, brief_revision, brief_fingerprint, direction_fp, copy_fp, seq, funding, '
         'copy_state, copy_reason, copy, copy_from, reservation_id, credits, record, offered_at, created_at, '
         'copy_ready_at')
FREE, BUSY, USED, NOT_CLAIMABLE = 'free', 'busy', 'used', 'not_claimable'


class SketchStoreMissing(RuntimeError):
    """Migration 049 is not applied on this database."""


@dataclass
class Sketch:
    id: str
    project_id: str
    account_id: str
    brief_revision: int
    brief_fingerprint: str
    direction_fp: str
    copy_fp: str
    seq: int
    funding: str
    copy_state: str
    copy_reason: str | None
    copy: dict | None
    copy_from: str | None
    reservation_id: str | None
    credits: int
    record: dict = field(default_factory=dict)
    offered_at: object = None
    created_at: object = None
    copy_ready_at: object = None


def _sketch(row) -> Sketch:
    return Sketch(*row)


def new_id() -> str:
    return f'skt_{uuid.uuid4().hex[:24]}'


class SketchStore:
    def __init__(self, pool):
        self.pool = pool

    def _run(self, fn):
        import psycopg
        try:
            return fn()
        except psycopg.errors.UndefinedTable as exc:
            raise SketchStoreMissing('migration 049_direction_sketches is not applied '
                                     '(infra/postgres/049_direction_sketches.sql)') from exc

    # -- create / read ------------------------------------------------------------------------------------------
    def create(self, *, project_id: str, account_id: str, brief_revision: int, brief_fingerprint: str,
               direction_fp: str, copy_fp: str, record: dict, seq: int = 0, copy: dict | None = None,
               copy_from: str | None = None) -> tuple[Sketch, bool]:
        """(the sketch, whether this call created it). Idempotent on (project, direction, copy, seq): the same request
        returns the row it made the first time. A sketch made with the words of an earlier one (`copy_from`, or `copy`)
        is `written` at once and costs nothing (funding 'none')."""
        state = 'written' if (copy is not None or copy_from) else 'none'

        def run():
            sid = new_id()
            with self.pool.connection() as conn:
                with conn.transaction(), conn.cursor() as cur:
                    cur.execute(
                        'INSERT INTO direction_sketches (id, project_id, account_id, brief_revision, brief_fingerprint, '
                        'direction_fp, copy_fp, seq, funding, copy_state, copy, copy_from, record, offered_at, '
                        'copy_ready_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, '
                        "now(), CASE WHEN %s = 'written' THEN now() END) "
                        'ON CONFLICT (project_id, direction_fp, copy_fp, seq) DO NOTHING RETURNING ' + _COLS,
                        (sid, project_id, account_id, brief_revision, brief_fingerprint, direction_fp, copy_fp, seq,
                         'none', state, None if copy is None else json.dumps(copy, ensure_ascii=False), copy_from,
                         json.dumps(record, ensure_ascii=False, default=str), state))
                    row = cur.fetchone()
                    if row is not None:
                        return _sketch(row), True
                    cur.execute(f'SELECT {_COLS} FROM direction_sketches WHERE project_id = %s AND direction_fp = %s '
                                'AND copy_fp = %s AND seq = %s AND account_id = %s',
                                (project_id, direction_fp, copy_fp, seq, account_id))
                    row = cur.fetchone()
                    if row is None:       # the same key under another account: never returned
                        raise PermissionError('sketch key belongs to another account')
                    return _sketch(row), False
        return self._run(run)

    def get(self, sketch_id: str, project_id: str, account_id: str) -> Sketch | None:
        def run():
            with self.pool.connection() as conn, conn.cursor() as cur:
                cur.execute(f'SELECT {_COLS} FROM direction_sketches WHERE id = %s AND project_id = %s '
                            'AND account_id = %s', (sketch_id, project_id, account_id))
                row = cur.fetchone()
            return None if row is None else _sketch(row)
        return self._run(run)

    def latest(self, project_id: str, account_id: str, *, limit: int = 20) -> list[Sketch]:
        def run():
            with self.pool.connection() as conn, conn.cursor() as cur:
                cur.execute(f'SELECT {_COLS} FROM direction_sketches WHERE project_id = %s AND account_id = %s '
                            'ORDER BY created_at DESC, id DESC LIMIT %s', (project_id, account_id, int(limit)))
                return [_sketch(r) for r in cur.fetchall()]
        return self._run(run)

    def written_copy(self, project_id: str, account_id: str, copy_fp: str) -> Sketch | None:
        """The newest sketch of this project whose words were written for these customer words (reused for free)."""
        def run():
            with self.pool.connection() as conn, conn.cursor() as cur:
                cur.execute(f"SELECT {_COLS} FROM direction_sketches WHERE project_id = %s AND account_id = %s "
                            "AND copy_fp = %s AND copy_state = 'written' AND copy IS NOT NULL "
                            'ORDER BY created_at DESC, id DESC LIMIT 1', (project_id, account_id, copy_fp))
                row = cur.fetchone()
            return None if row is None else _sketch(row)
        return self._run(run)

    # -- the words: claim, attach, finish -------------------------------------------------------------------------
    def claim(self, sketch_id: str, project_id: str, account_id: str, funding: str) -> str:
        """none|failed -> pending with `funding`. FREE when this call holds the sketch's model call. For the company's
        first sketch ('company_first') the partial unique index decides: a project has one pending-or-written free
        sketch, so a second claim gets BUSY (one is pending) or USED (one was written). Another state: NOT_CLAIMABLE."""
        if funding not in FUNDING or funding == 'none':
            raise ValueError(f'a claim funds the words: one of {FUNDING[1:]}, not {funding!r}')
        import psycopg

        def run():
            with self.pool.connection() as conn:
                try:
                    with conn.transaction(), conn.cursor() as cur:
                        cur.execute("UPDATE direction_sketches SET funding = %s, copy_state = 'pending', "
                                    'copy_reason = NULL WHERE id = %s AND project_id = %s AND account_id = %s '
                                    "AND copy_state IN ('none', 'failed') RETURNING id",
                                    (funding, sketch_id, project_id, account_id))
                        return FREE if cur.fetchone() is not None else NOT_CLAIMABLE
                except psycopg.errors.UniqueViolation:
                    with conn.cursor() as cur:
                        cur.execute("SELECT copy_state FROM direction_sketches WHERE project_id = %s AND "
                                    "funding = 'company_first' AND copy_state IN ('pending', 'written') LIMIT 1",
                                    (project_id,))
                        row = cur.fetchone()
                    return BUSY if row and row[0] == 'pending' else USED
        return self._run(run)

    def set_reservation(self, sketch_id: str, reservation_id: str) -> None:
        def run():
            with self.pool.connection() as conn:
                with conn.transaction(), conn.cursor() as cur:
                    cur.execute('UPDATE direction_sketches SET reservation_id = %s WHERE id = %s',
                                (reservation_id, sketch_id))
        self._run(run)

    def finish(self, sketch_id: str, state: str, *, reason: str | None = None, copy: dict | None = None) -> bool:
        """pending -> written | failed, once: a second call (a second finalise) changes nothing and says False."""
        if state not in ('written', 'failed'):
            raise ValueError('a pending sketch finishes as written or failed')
        if (state == 'written') != (copy is not None):
            raise ValueError('written needs the words, failed has none')

        def run():
            with self.pool.connection() as conn:
                with conn.transaction(), conn.cursor() as cur:
                    cur.execute("UPDATE direction_sketches SET copy_state = %s, copy_reason = %s, copy = %s::jsonb, "
                                "copy_ready_at = CASE WHEN %s = 'written' THEN now() END "
                                "WHERE id = %s AND copy_state = 'pending' RETURNING id",
                                (state, None if reason is None else reason[:300],
                                 None if copy is None else json.dumps(copy, ensure_ascii=False), state, sketch_id))
                    return cur.fetchone() is not None
        return self._run(run)

    def free_taken(self, project_id: str, account_id: str) -> bool:
        """The company's free sketch of this project is pending or written (the partial unique index's own predicate)."""
        def run():
            with self.pool.connection() as conn, conn.cursor() as cur:
                cur.execute("SELECT EXISTS (SELECT 1 FROM direction_sketches WHERE project_id = %s AND account_id = %s "
                            "AND funding = 'company_first' AND copy_state IN ('pending', 'written'))", (project_id, account_id))
                return bool(cur.fetchone()[0])
        return self._run(run)

    def attempts(self, project_id: str, account_id: str, purpose: str = 'sketch-free') -> int:
        """How many model calls this project's sketches reserved on a scope (any state): the bound of the free sketch's
        retries. Counted from the reservations themselves, so a retry that failed still counts."""
        scope = f'{purpose}:{account_id}:{project_id}'

        def run():
            with self.pool.connection() as conn, conn.cursor() as cur:
                cur.execute('SELECT count(*) FROM intake_reservation_scopes WHERE scope = %s', (scope,))
                return int(cur.fetchone()[0])
        return self._run(run)
