"""Durable conversation + plan storage (migration 036).

The brief (project_briefs, immutable revisions) is the source of truth for
requirements. These tables hold what happened around it:
  intake_messages   every customer/assistant turn, bound to the brief revision
                    it produced, with the interpreter used and its cost
  execution_plans   each Chief Architect plan, keyed by the brief fingerprint
Writes are idempotent per request_key (a retried send never duplicates).
"""
from __future__ import annotations

import json
import uuid
from decimal import Decimal


class MemoryConversationStore:
    def __init__(self):
        self.messages: list[dict] = []
        self.plans: dict[tuple[str, str], dict] = {}

    def add_message(self, *, project_id, account_id, role, content, brief_revision=None, interpretation=None,
                    interpreter='deterministic', cost_usd=Decimal('0'), request_key=None) -> dict:
        for m in self.messages:
            if request_key and m['project_id'] == project_id and m['request_key'] == request_key and m['role'] == role:
                return m
        row = {'id': len(self.messages) + 1, 'project_id': project_id, 'account_id': account_id, 'role': role,
               'content': content[:8000], 'brief_revision': brief_revision, 'interpretation': interpretation or {},
               'interpreter': interpreter, 'cost_usd': str(cost_usd), 'request_key': request_key}
        self.messages.append(row)
        return row

    def messages_for(self, project_id, limit=200) -> list[dict]:
        return [m for m in self.messages if m['project_id'] == project_id][-limit:]

    def find_reply(self, project_id, request_key):
        return next((m for m in self.messages if m['project_id'] == project_id and m['request_key'] == request_key
                     and m['role'] == 'assistant'), None)

    def conversation_cost(self, project_id) -> Decimal:
        return sum((Decimal(m['cost_usd']) for m in self.messages if m['project_id'] == project_id), Decimal('0'))

    def save_plan(self, *, project_id, brief_revision, brief_fingerprint, plan) -> dict:
        key = (project_id, plan['graph_fingerprint'] + plan['requirements_fingerprint'])
        if key not in self.plans:
            self.plans[key] = {'id': f'pln_{uuid.uuid4().hex[:20]}', 'project_id': project_id, 'brief_revision': brief_revision,
                               'brief_fingerprint': brief_fingerprint, 'plan': plan}
        return self.plans[key]

    def plan_for(self, project_id, brief_fingerprint):
        rows = [p for (pid, _), p in self.plans.items() if pid == project_id and p['brief_fingerprint'] == brief_fingerprint]
        return rows[-1] if rows else None


class PostgresConversationStore:
    def __init__(self, pool):
        self.pool = pool

    _MSG = 'id, project_id, account_id, role, content, brief_revision, interpretation, interpreter, cost_usd, request_key'

    def _row(self, r) -> dict:
        d = dict(zip([c.strip() for c in self._MSG.split(',')], r))
        d['cost_usd'] = str(d['cost_usd'])
        return d

    def add_message(self, *, project_id, account_id, role, content, brief_revision=None, interpretation=None,
                    interpreter='deterministic', cost_usd=Decimal('0'), request_key=None) -> dict:
        with self.pool.connection() as conn:
            with conn.transaction():
                r = conn.execute(
                    f'INSERT INTO intake_messages (project_id, account_id, role, content, brief_revision, interpretation, '
                    f'interpreter, cost_usd, request_key) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s) '
                    f'ON CONFLICT (project_id, request_key, role) WHERE request_key IS NOT NULL DO NOTHING RETURNING {self._MSG}',
                    (project_id, account_id, role, content[:8000], brief_revision, json.dumps(interpretation or {}, default=str),
                     interpreter, cost_usd, request_key)).fetchone()
                if r is None:
                    r = conn.execute(f'SELECT {self._MSG} FROM intake_messages WHERE project_id = %s AND request_key = %s AND role = %s',
                                     (project_id, request_key, role)).fetchone()
        return self._row(r)

    def messages_for(self, project_id, limit=200) -> list[dict]:
        with self.pool.connection() as conn:
            rows = conn.execute(f'SELECT {self._MSG} FROM intake_messages WHERE project_id = %s ORDER BY id DESC LIMIT %s',
                                (project_id, limit)).fetchall()
        return [self._row(r) for r in reversed(rows)]

    def find_reply(self, project_id, request_key):
        if not request_key:
            return None
        with self.pool.connection() as conn:
            r = conn.execute(f"SELECT {self._MSG} FROM intake_messages WHERE project_id = %s AND request_key = %s AND role = 'assistant'",
                             (project_id, request_key)).fetchone()
        return self._row(r) if r else None

    def conversation_cost(self, project_id) -> Decimal:
        with self.pool.connection() as conn:
            v = conn.execute('SELECT COALESCE(sum(cost_usd), 0) FROM intake_messages WHERE project_id = %s', (project_id,)).fetchone()[0]
        return Decimal(str(v))

    def save_plan(self, *, project_id, brief_revision, brief_fingerprint, plan) -> dict:
        fp = plan['graph_fingerprint'][:32] + plan['requirements_fingerprint'][:32]
        pid = f'pln_{uuid.uuid4().hex[:20]}'
        with self.pool.connection() as conn:
            with conn.transaction():
                r = conn.execute(
                    'INSERT INTO execution_plans (id, project_id, brief_revision, brief_fingerprint, plan_schema, fingerprint, plan) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb) ON CONFLICT (project_id, fingerprint) DO NOTHING RETURNING id',
                    (pid, project_id, brief_revision, brief_fingerprint, plan['schema'], fp, json.dumps(plan, default=str))).fetchone()
                if r is None:
                    pid = conn.execute('SELECT id FROM execution_plans WHERE project_id = %s AND fingerprint = %s',
                                       (project_id, fp)).fetchone()[0]
        return {'id': pid, 'project_id': project_id, 'brief_revision': brief_revision, 'brief_fingerprint': brief_fingerprint,
                'plan': plan}

    def plan_for(self, project_id, brief_fingerprint):
        with self.pool.connection() as conn:
            r = conn.execute('SELECT id, brief_revision, plan FROM execution_plans WHERE project_id = %s AND brief_fingerprint = %s '
                             'ORDER BY created_at DESC LIMIT 1', (project_id, brief_fingerprint)).fetchone()
        return None if r is None else {'id': r[0], 'project_id': project_id, 'brief_revision': r[1],
                                       'brief_fingerprint': brief_fingerprint, 'plan': r[2]}
