"""Durable ProjectBrief revisions and build approvals (migration 030;
master directive 2026-10-09 §4-5).

Revisions are immutable rows written with compare-and-set: a writer states
the revision it read; if another write got there first the UNIQUE constraint
fails and the caller gets StaleBrief (409), never a silent overwrite. A retry
with the same request key returns the revision it already made.

An approval binds user, project, brief revision + fingerprint, contract +
fingerprint and the budget quote for APPROVAL_TTL. `consume` runs inside the
build's reservation transaction, locks the approval row and checks every
binding again, so a direct API call, a refresh or a race cannot start a build
the user did not approve.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .discovery import Brief, complete

APPROVAL_TTL = timedelta(minutes=int(os.getenv('OMNI_APPROVAL_TTL_MINUTES', '30')))


class StaleBrief(RuntimeError):
    pass


class ApprovalError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}            # O10: e.g. {'pending': [...], 'contradictions': [...]}


@dataclass(frozen=True)
class BriefRow:
    id: str
    project_id: str
    revision: int
    brief: Brief
    complete: bool
    fingerprint: str

    def to_dict(self) -> dict:
        return {'id': self.id, 'revision': self.revision, 'complete': self.complete, 'fingerprint': self.fingerprint,
                'mode': self.brief.mode}


def _row(r) -> BriefRow:
    data = r[3] if isinstance(r[3], dict) else json.loads(r[3])
    return BriefRow(r[0], r[1], int(r[2]), Brief.from_dict(data), bool(r[4]), r[5])


_SELECT = "SELECT id, project_id, revision, brief_json, complete, fingerprint FROM project_briefs"


class PostgresBriefRepository:
    def __init__(self, pool):
        self.pool = pool

    def latest(self, project_id: str, cur=None) -> BriefRow | None:
        sql = _SELECT + " WHERE project_id = %s ORDER BY revision DESC LIMIT 1"
        if cur is not None:
            cur.execute(sql, (project_id,))
            r = cur.fetchone()
            return _row(r) if r else None
        with self.pool.connection() as conn:
            r = conn.execute(sql, (project_id,)).fetchone()
        return _row(r) if r else None

    def save(self, *, project_id: str, account_id: str, brief: Brief, expected_revision: int,
             request_key: str | None = None) -> BriefRow:
        """Write revision expected_revision + 1. StaleBrief if someone else wrote first."""
        import psycopg
        bid = f'brf_{uuid.uuid4().hex}'
        payload = json.dumps(brief.to_dict(), ensure_ascii=False)
        try:
            with self.pool.connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        if request_key:
                            cur.execute(_SELECT + " WHERE project_id = %s AND request_key = %s", (project_id, request_key))
                            r = cur.fetchone()
                            if r:
                                return _row(r)
                        current = self.latest(project_id, cur)
                        if (current.revision if current else 0) != expected_revision:
                            raise StaleBrief(f'brief changed (now revision {current.revision if current else 0})')
                        cur.execute(
                            "INSERT INTO project_briefs (id, project_id, revision, account_id, mode, complete, brief_json,"
                            " fingerprint, request_key) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)",
                            (bid, project_id, expected_revision + 1, account_id, brief.mode, complete(brief), payload,
                             brief.fingerprint(), request_key))
        except psycopg.errors.UniqueViolation as exc:
            if request_key:
                with self.pool.connection() as conn:
                    r = conn.execute(_SELECT + " WHERE project_id = %s AND request_key = %s", (project_id, request_key)).fetchone()
                if r:
                    return _row(r)
            raise StaleBrief('brief changed by a concurrent request') from exc
        return BriefRow(bid, project_id, expected_revision + 1, brief, complete(brief), brief.fingerprint())

    # ---- approvals ----------------------------------------------------------

    def create_approval(self, *, project_id: str, account_id: str, brief_row: BriefRow, build_contract_id: str,
                        contract_fingerprint: str, budget_fingerprint: str, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        aid = f'apr_{uuid.uuid4().hex}'
        expires = now + APPROVAL_TTL
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    current = self.latest(project_id, cur)
                    if current is None or current.revision != brief_row.revision:
                        raise ApprovalError('approval_stale', 'the request changed; review the new summary first')
                    if not current.complete:
                        from .discovery import missing
                        raise ApprovalError('brief_incomplete', 'some questions are still open', missing(current.brief))
                    # One active approval per project: an older one is superseded.
                    cur.execute("UPDATE build_approvals SET status = 'INVALIDATED', invalidated_reason = 'superseded'"
                                " WHERE project_id = %s AND status = 'ACTIVE'", (project_id,))
                    cur.execute(
                        "INSERT INTO build_approvals (id, project_id, account_id, brief_id, brief_revision, brief_fingerprint,"
                        " build_contract_id, contract_fingerprint, budget_fingerprint, status, expires_at)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s)",
                        (aid, project_id, account_id, brief_row.id, brief_row.revision, brief_row.fingerprint,
                         build_contract_id, contract_fingerprint, budget_fingerprint, expires))
        return {'approval_id': aid, 'expires_at': expires.isoformat(), 'brief_revision': brief_row.revision}

    def consume(self, cur, *, approval_id: str, project_id: str, account_id: str, build_contract_id: str,
                contract_fingerprint: str, budget_fingerprint: str, build_id: str) -> dict:
        """Inside the build transaction. Raises ApprovalError; on success the
        approval is USED by build_id (one approval -> one build)."""
        cur.execute("SELECT project_id, account_id, brief_revision, brief_fingerprint, build_contract_id, contract_fingerprint,"
                    " budget_fingerprint, status, expires_at, used_by_build_id FROM build_approvals WHERE id = %s FOR UPDATE",
                    (approval_id,))
        r = cur.fetchone()
        if r is None or r[0] != project_id or r[1] != account_id:
            raise ApprovalError('approval_not_found', 'no such approval for this project and user')
        status, expires = r[7], r[8]
        if status == 'USED':
            raise ApprovalError('approval_used', f'this approval already started build {r[9]}')
        if status != 'ACTIVE':
            raise ApprovalError('approval_stale', 'this approval is no longer valid; approve again')
        if expires <= datetime.now(timezone.utc):
            cur.execute("UPDATE build_approvals SET status = 'EXPIRED' WHERE id = %s", (approval_id,))
            raise ApprovalError('approval_expired', 'the approval expired; review and approve again')
        reason = None
        latest = self.latest(project_id, cur)
        if latest is None or latest.revision != r[2] or latest.fingerprint != r[3]:
            reason = 'the request changed after approval'
        elif r[4] != build_contract_id or r[5] != contract_fingerprint:
            reason = 'the plan changed after approval'
        elif r[6] != budget_fingerprint:
            reason = 'the price or budget changed after approval'
        if reason:
            cur.execute("UPDATE build_approvals SET status = 'INVALIDATED', invalidated_reason = %s WHERE id = %s",
                        (reason, approval_id))
            raise ApprovalError('approval_stale', reason)
        cur.execute("UPDATE build_approvals SET status = 'USED', used_by_build_id = %s WHERE id = %s", (build_id, approval_id))
        return {'approval_id': approval_id, 'brief_revision': r[2], 'brief_fingerprint': r[3]}
