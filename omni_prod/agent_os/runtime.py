"""AgentRuntime: durable task graph with permissions, budgets, handoffs,
memory, evidence and independent verification (autonomous completion §12-13).

Everything is stored in Postgres (migration 034), so a task's state survives
a process, worker or server restart; `resume()` puts the run's interrupted
tasks back to READY. Engines enforced on every call:

  PermissionEngine     an agent may use only its contract's allowed skills and
                       never a forbidden one
  BudgetEngine         a task's recorded cost may not exceed its budget, and
                       the run's total may not exceed the run budget
  VerificationEngine   a task is verified only by a SUCCEEDED task of a
                       different agent; producers with separation-of-duties
                       rules need one of their named verifiers
"""
from __future__ import annotations

import json
import uuid
from decimal import Decimal

from .agents import BY_KEY as AGENTS, SEPARATION_OF_DUTIES

STATES = ('PENDING', 'READY', 'RUNNING', 'WAITING', 'BLOCKED', 'VERIFYING', 'REPAIRING', 'SUCCEEDED', 'FAILED',
          'CANCEL_REQUESTED', 'CANCELLED')
TERMINAL = {'SUCCEEDED', 'FAILED', 'CANCELLED'}
ALLOWED = {
    'PENDING': {'READY', 'BLOCKED', 'CANCELLED'},
    'READY': {'RUNNING', 'BLOCKED', 'CANCELLED'},
    'RUNNING': {'VERIFYING', 'REPAIRING', 'WAITING', 'SUCCEEDED', 'FAILED', 'CANCEL_REQUESTED', 'BLOCKED', 'READY'},
    'WAITING': {'RUNNING', 'CANCELLED', 'FAILED'},
    'BLOCKED': {'READY', 'FAILED', 'CANCELLED'},
    'VERIFYING': {'SUCCEEDED', 'FAILED', 'REPAIRING', 'READY'},
    'REPAIRING': {'RUNNING', 'VERIFYING', 'FAILED', 'CANCEL_REQUESTED', 'READY'},
    'CANCEL_REQUESTED': {'CANCELLED'},
    'SUCCEEDED': set(), 'FAILED': set(), 'CANCELLED': set(),
}


class RuntimeViolation(RuntimeError):
    """A permission, budget, dependency, state or verification rule was broken."""


class PermissionEngine:
    @staticmethod
    def check(agent_key: str, skills) -> None:
        contract = AGENTS.get(agent_key)
        if contract is None:
            raise RuntimeViolation(f'unknown agent {agent_key!r}')
        for skill in skills:
            if skill in contract.forbidden_skills or skill not in contract.allowed_skills:
                raise RuntimeViolation(f'agent {agent_key} may not use skill {skill!r}')


class VerificationEngine:
    @staticmethod
    def check(producer_agent: str, verifier_agent: str) -> None:
        if producer_agent == verifier_agent:
            raise RuntimeViolation(f'{producer_agent} cannot verify its own work')
        required = SEPARATION_OF_DUTIES.get(producer_agent)
        if required and verifier_agent not in required:
            raise RuntimeViolation(f'{producer_agent} must be verified by one of {required}, not {verifier_agent}')


class AgentRuntime:
    def __init__(self, pool):
        self.pool = pool

    # ---------------------------------------------------------------- runs
    def create_run(self, subject_kind: str, subject_id: str, *, budget_usd: Decimal | None = None) -> str:
        run_id = f'run_{uuid.uuid4().hex[:20]}'
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute('INSERT INTO agent_runs(id, subject_kind, subject_id, budget_usd) VALUES (%s, %s, %s, %s)',
                             (run_id, subject_kind, subject_id, budget_usd))
        return run_id

    def supersede_open_runs(self, subject_kind: str, subject_id: str) -> int:
        """A recovered build starts a new run; the run of the lost worker is
        closed as 'superseded' and its unfinished tasks FAILED (worker lost)."""
        with self.pool.connection() as conn:
            with conn.transaction():
                ids = [r[0] for r in conn.execute(
                    'SELECT id FROM agent_runs WHERE subject_kind = %s AND subject_id = %s AND finished_at IS NULL FOR UPDATE',
                    (subject_kind, subject_id)).fetchall()]
                if ids:
                    conn.execute("UPDATE agent_tasks SET state = 'FAILED', finished_at = now(), "
                                 "evidence = evidence || '{\"failed\": \"worker lost; run superseded by recovery\"}'::jsonb "
                                 "WHERE run_id = ANY(%s) AND state NOT IN ('SUCCEEDED', 'FAILED', 'CANCELLED')", (ids,))
                    conn.execute("UPDATE agent_runs SET finished_at = now(), outcome = 'superseded' WHERE id = ANY(%s)", (ids,))
        return len(ids)

    def finish_run(self, run_id: str, outcome: str) -> None:
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute('UPDATE agent_runs SET finished_at = now(), outcome = %s WHERE id = %s', (outcome, run_id))

    # --------------------------------------------------------------- tasks
    def add_task(self, run_id: str, agent_key: str, *, skills=(), depends_on=(), budget_usd: Decimal | None = None,
                 evidence: dict | None = None) -> str:
        PermissionEngine.check(agent_key, skills)
        task_id = f'tsk_{uuid.uuid4().hex[:20]}'
        state = 'READY' if not depends_on else 'PENDING'
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute('INSERT INTO agent_tasks(id, run_id, agent_key, skill_keys, state, depends_on, budget_usd, evidence) '
                             'VALUES (%s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb)',
                             (task_id, run_id, agent_key, json.dumps(list(skills)), state, json.dumps(list(depends_on)),
                              budget_usd, json.dumps(evidence or {}, default=str)))
        return task_id

    def get(self, task_id: str) -> dict:
        with self.pool.connection() as conn:
            row = conn.execute('SELECT id, run_id, agent_key, state, depends_on, cost_usd, budget_usd, verified_by_task, '
                               'attempt, evidence FROM agent_tasks WHERE id = %s', (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return dict(zip(('id', 'run_id', 'agent_key', 'state', 'depends_on', 'cost_usd', 'budget_usd',
                         'verified_by_task', 'attempt', 'evidence'), row))

    def transition(self, task_id: str, target: str, *, evidence: dict | None = None, cost_usd: Decimal | None = None) -> None:
        if target not in STATES:
            raise RuntimeViolation(f'unknown state {target}')
        blocked = None
        with self.pool.connection() as conn:
            with conn.transaction():
                row = conn.execute('SELECT state, depends_on, budget_usd, cost_usd, run_id FROM agent_tasks WHERE id = %s '
                                   'FOR UPDATE', (task_id,)).fetchone()
                if row is None:
                    raise KeyError(task_id)
                state, deps, budget, cost, run_id = row
                if target not in ALLOWED[state]:
                    raise RuntimeViolation(f'illegal task transition {state} -> {target}')
                if target == 'RUNNING' and deps:
                    done = conn.execute("SELECT count(*) FROM agent_tasks WHERE id = ANY(%s) AND state = 'SUCCEEDED'",
                                        (list(deps),)).fetchone()[0]
                    if done != len(deps):
                        raise RuntimeViolation('dependencies are not all SUCCEEDED')
                new_cost = Decimal(str(cost)) + (Decimal(str(cost_usd)) if cost_usd else Decimal('0'))
                if budget is not None and new_cost > Decimal(str(budget)):
                    conn.execute("UPDATE agent_tasks SET state = 'BLOCKED', evidence = evidence || %s::jsonb WHERE id = %s",
                                 (json.dumps({'blocked': f'budget {budget} exceeded by {new_cost}'}), task_id))
                    blocked = f'task budget {budget} exceeded ({new_cost})'  # committed, then raised below
                else:
                    self._apply(conn, task_id, target, new_cost, evidence, run_id, cost_usd)
        if blocked:
            raise RuntimeViolation(blocked)

    def _apply(self, conn, task_id, target, new_cost, evidence, run_id, cost_usd) -> None:
        run_budget = conn.execute('SELECT budget_usd FROM agent_runs WHERE id = %s', (run_id,)).fetchone()[0]
        if run_budget is not None and cost_usd:
            spent = conn.execute('SELECT COALESCE(sum(cost_usd), 0) FROM agent_tasks WHERE run_id = %s AND id <> %s',
                                 (run_id, task_id)).fetchone()[0]
            if Decimal(str(spent)) + new_cost > Decimal(str(run_budget)):
                raise RuntimeViolation(f'run budget {run_budget} exceeded')
        conn.execute(
            'UPDATE agent_tasks SET state = %s, cost_usd = %s, evidence = evidence || %s::jsonb, '
            "started_at = CASE WHEN %s = 'RUNNING' THEN COALESCE(started_at, now()) ELSE started_at END, "
            'finished_at = CASE WHEN %s IN (\'SUCCEEDED\', \'FAILED\', \'CANCELLED\') THEN now() ELSE finished_at END '
            'WHERE id = %s',
            (target, new_cost, json.dumps(evidence or {}, default=str), target, target, task_id))
        if target == 'FAILED':  # Wave A §6.2: a failure invalidates (only) its downstream tasks
            frontier = [task_id]
            while frontier:
                rows = conn.execute(
                    "UPDATE agent_tasks t SET state = 'BLOCKED', evidence = evidence || %s::jsonb "
                    "WHERE t.run_id = %s AND t.state IN ('PENDING', 'READY') AND t.depends_on ?| %s::text[] RETURNING t.id",
                    (json.dumps({'blocked': 'upstream task failed'}), run_id, frontier)).fetchall()
                frontier = [r[0] for r in rows]
        if target == 'SUCCEEDED':  # dependents whose deps are all done become READY
            conn.execute(
                "UPDATE agent_tasks t SET state = 'READY' WHERE t.run_id = %s AND t.state = 'PENDING' AND NOT EXISTS ("
                " SELECT 1 FROM jsonb_array_elements_text(t.depends_on) d JOIN agent_tasks x ON x.id = d"
                " WHERE x.state <> 'SUCCEEDED')", (run_id,))

    def handoff(self, from_task: str, to_agent: str, payload: dict) -> None:
        task = self.get(from_task)
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute('INSERT INTO agent_handoffs(run_id, from_task, to_agent, payload) VALUES (%s, %s, %s, %s::jsonb)',
                             (task['run_id'], from_task, to_agent, json.dumps(payload, default=str)))

    def verify(self, task_id: str, verifier_task_id: str) -> None:
        producer, verifier = self.get(task_id), self.get(verifier_task_id)
        VerificationEngine.check(producer['agent_key'], verifier['agent_key'])
        if verifier['state'] != 'SUCCEEDED':
            raise RuntimeViolation('the verifier task has not succeeded')
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute('UPDATE agent_tasks SET verified_by_task = %s WHERE id = %s', (verifier_task_id, task_id))

    def request_cancel(self, run_id: str) -> int:
        with self.pool.connection() as conn:
            with conn.transaction():
                n = conn.execute("UPDATE agent_tasks SET state = 'CANCEL_REQUESTED' WHERE run_id = %s AND state = 'RUNNING'",
                                 (run_id,)).rowcount
                n += conn.execute("UPDATE agent_tasks SET state = 'CANCELLED', finished_at = now() WHERE run_id = %s "
                                  "AND state IN ('PENDING', 'READY', 'WAITING', 'BLOCKED')", (run_id,)).rowcount
        return n

    def resume(self, run_id: str) -> list[str]:
        """After a restart: interrupted RUNNING/VERIFYING/REPAIRING tasks go back
        to READY with attempt + 1 (their work is redone, never assumed)."""
        with self.pool.connection() as conn:
            with conn.transaction():
                rows = conn.execute("UPDATE agent_tasks SET state = 'READY', attempt = attempt + 1 WHERE run_id = %s "
                                    "AND state IN ('RUNNING', 'VERIFYING', 'REPAIRING') RETURNING id", (run_id,)).fetchall()
        return [r[0] for r in rows]

    # -------------------------------------------------------------- memory
    def remember(self, project_id: str, agent_key: str, key: str, value) -> None:
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute('INSERT INTO agent_memory(project_id, agent_key, key, value) VALUES (%s, %s, %s, %s::jsonb) '
                             'ON CONFLICT (project_id, agent_key, key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()',
                             (project_id, agent_key, key, json.dumps(value, default=str)))

    def recall(self, project_id: str, agent_key: str, key: str):
        with self.pool.connection() as conn:
            row = conn.execute('SELECT value FROM agent_memory WHERE project_id = %s AND agent_key = %s AND key = %s',
                               (project_id, agent_key, key)).fetchone()
        return row[0] if row else None

    # --------------------------------------------------------------- reads
    def tasks(self, run_id: str) -> list[dict]:
        with self.pool.connection() as conn:
            rows = conn.execute('SELECT id, agent_key, state, cost_usd, verified_by_task, attempt, depends_on, evidence FROM agent_tasks '
                                'WHERE run_id = %s ORDER BY created_at', (run_id,)).fetchall()
        return [dict(zip(('id', 'agent_key', 'state', 'cost_usd', 'verified_by_task', 'attempt', 'depends_on', 'evidence'), r))
                for r in rows]
