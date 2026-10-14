"""Records a real build as a durable agent task graph (autonomous completion §12).

Wired into BuildControl: every model call and every sandbox run of the real
pipeline becomes a task of the agent that does that work; the end of the build
adds the browser, acceptance, security, cost, release and quality-gate tasks
from the build's own evidence, with independent verification links. These
rows are what the capability auditor reads as runtime truth ("this agent ran
and another agent verified it"). Recording is best effort: it never changes a
build's outcome.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from .runtime import AgentRuntime, RuntimeViolation

_log = logging.getLogger(__name__)

MODEL_TASK_AGENT = {
    'architecture': ('architecture_agent', ('data_model_design', 'api_contract_design')),
    'codegen': ('coding_agent', ('file_create',)),
    'repair': ('repair_agent', ('minimal_patch_generation', 'repair_execution')),
    'review': ('code_review_agent', ('xss_check',)),
    'modification': ('product_evolution_agent', ('file_modify',)),
    'classification': ('product_evolution_agent', ()),
}


class BuildAgentRecorder:
    def __init__(self, pool, subject_id: str, *, subject_kind: str = 'build', budget_usd=None):
        self.rt = AgentRuntime(pool)
        self.subject_id = subject_id
        self.subject_kind = subject_kind
        self.budget = budget_usd
        self.run_id = None
        self.current = None        # (task_id, agent_key)
        self.done: dict[str, str] = {}  # agent_key -> last SUCCEEDED task id
        self.failed_qa = False

    def _safe(self, fn, *a, **k):
        try:
            return fn(*a, **k)
        except Exception as exc:  # recording must never fail the build
            _log.warning('agent recorder: %s', exc)
            return None

    def start(self, *, from_brief: bool) -> None:
        def go():
            self.rt.supersede_open_runs(self.subject_kind, self.subject_id)
            self.run_id = self.rt.create_run(self.subject_kind, self.subject_id, budget_usd=self.budget)
            if self.subject_kind == 'build':
                for agent, skills in (('discovery_agent', ('safe_default_selection',)) if from_brief else (None, ()),
                                      ('requirements_agent', ('requirement_extraction',)),
                                      ('product_planner', ('build_plan_generation',))):
                    if agent:
                        tid = self.rt.add_task(self.run_id, agent, skills=skills)
                        self.rt.transition(tid, 'RUNNING')
                        self.rt.transition(tid, 'SUCCEEDED', evidence={'source': 'approved brief/contract'})
                        self.done[agent] = tid
        self._safe(go)

    def _close_current(self, state: str = 'SUCCEEDED', evidence: dict | None = None) -> None:
        if self.current is None:
            return
        tid, agent = self.current
        self._safe(self.rt.transition, tid, state, evidence=evidence or {})
        if state == 'SUCCEEDED':
            self.done[agent] = tid
        self.current = None

    def _open(self, agent: str, skills=(), cost: Decimal | None = None) -> None:
        if self.run_id is None:
            return
        tid = self._safe(self.rt.add_task, self.run_id, agent, skills=skills)
        if tid:
            self._safe(self.rt.transition, tid, 'RUNNING')
            self.current = (tid, agent)

    def on_model(self, task: str) -> None:
        agent, skills = MODEL_TASK_AGENT.get(task, (None, ()))
        if agent is None or (self.current and self.current[1] == agent):
            return
        self._close_current()
        self._open(agent, skills)

    def on_check(self, passed: bool, summary: str) -> None:
        self._close_current()
        self._open('qa_agent', ('unit_test_execution',))
        # Not a verification of the coding agent: the tests that ran were
        # written by the coding agent (audit 2026-10-10, self-certification).
        self._close_current('SUCCEEDED' if passed else 'FAILED', {'summary': summary[:300],
                                                                  'tests_written_by': 'coding_agent'})

    def finish(self, *, status: str, evidence: dict | None) -> None:
        if self.run_id is None:
            return
        self._close_current('SUCCEEDED' if status == 'ready' else ('CANCELLED' if status == 'cancelled' else 'FAILED'))
        ev = evidence or {}
        final = []
        bc = ev.get('browser_check') or {}
        if bc:
            final.append(('browser_rehearsal_agent', ('browser_launch', 'form_test'), bc.get('status') == 'passed', bc.get('status')))
        ba = (ev.get('behavior_acceptance') or {}).get('last') or {}
        if ba:
            final.append(('behavioral_acceptance_agent', ('behavioral_acceptance_test',), ba.get('status') == 'PASS', ba.get('summary')))
        gates = ev.get('gates') or {}
        if 'security' in gates:
            final.append(('security_agent', ('secret_detection', 'security_release_gate'), bool(gates['security'].get('passed')), 'static scan'))
        settlement = ev.get('economics_settlement') or {}
        if settlement:
            basis = (settlement.get('cost_basis') or {}).get('llm') or ''
            # Succeeds only when the cost is actually known (metered/reported), not on any settlement.
            final.append(('cost_economics_agent', ('credit_settlement',), not str(basis).startswith('UNKNOWN'), basis))
        if status == 'ready':
            final.append(('release_agent', ('version_create', 'release_gate'), True, 'version committed'))
        for agent, skills, ok, note in final:
            tid = self._safe(self.rt.add_task, self.run_id, agent, skills=skills)
            if tid:
                self._safe(self.rt.transition, tid, 'RUNNING')
                self._safe(self.rt.transition, tid, 'SUCCEEDED' if ok else 'FAILED', evidence={'note': str(note)[:200]})
                if ok:
                    self.done[agent] = tid
        qr = ev.get('quality_report') or {}
        gate = self._safe(self.rt.add_task, self.run_id, 'quality_gate_agent')
        if gate:
            self._safe(self.rt.transition, gate, 'RUNNING')
            # The release policy is the independent decision (platform-owned checks).
            ok = status == 'ready' and qr.get('decision') == 'READY'
            self._safe(self.rt.transition, gate, 'SUCCEEDED' if ok else 'FAILED',
                       evidence={'status': status, 'policy': qr.get('policy_version'), 'decision': qr.get('decision'),
                                 'artifact_sha256': qr.get('artifact_sha256'), 'blocking': qr.get('blocking')})
            if ok:
                for agent in ('coding_agent', 'repair_agent', 'release_agent', 'behavioral_acceptance_agent',
                              'browser_rehearsal_agent', 'security_agent', 'cost_economics_agent', 'qa_agent'):
                    if agent in self.done:
                        self._safe(self.rt.verify, self.done[agent], gate)
        self._safe(self.rt.finish_run, self.run_id, status)


__all__ = ['BuildAgentRecorder', 'PlanAdmittedExecutor', 'PlanBoundRecorder', 'PlanViolation', 'RuntimeViolation', 'recorder_for']


# ---------------------------------------------------------------------------
# Wave A: the approved execution plan drives the task graph.
# ---------------------------------------------------------------------------
MODEL_TASK_STAGE = {'architecture': 'architecture', 'codegen': 'codegen', 'repair': 'repair', 'review': 'review'}
# Release-policy check that decides each verification stage (platform-owned).
STAGE_CHECK = {'preview': 'preview_starts', 'behavior': 'behavioural_acceptance', 'browser': 'browser_flow',
               'visual': 'visual_layout_desktop_mobile', 'security': 'static_security_scan',
               'review': 'qa_review_blocking_findings'}


class PlanViolation(RuntimeError):
    """A plan-governed build tried a step the approved execution plan does not
    admit now (out of order, repeated, over its iteration limit or budget, or
    without durable plan state). The build fails closed: error plan_violation."""


class PlanAdmittedExecutor:
    """Outermost executor wrapper of a plan-governed build: no verification run
    starts unless the plan admits it (on_check_start). Keeps `_inner` so the
    worker's find_in_chain still reaches every executor of the chain."""

    def __init__(self, inner, recorder: 'PlanBoundRecorder'):
        self._inner = inner
        self._recorder = recorder

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        self._recorder.on_check_start()
        return self._inner.execute(repository=repository, spec=spec)


class PlanBoundRecorder(BuildAgentRecorder):
    """Materializes the Chief Architect's validated DAG as durable agent tasks
    BEFORE the engine runs (PENDING with real depends_on), then moves each
    task through its states as the existing engine performs the bound stage.

    Truth rules: a task is SUCCEEDED only when its stage actually happened and
    passed (stage results come from the platform-owned release policy, not the
    author); a failure BLOCKS its downstream tasks (runtime cascade); tasks the
    build never reached end CANCELLED with 'not reached'; non-executable tasks
    are BLOCKED with their gap. Recording never changes the build outcome.
    """

    def __init__(self, pool, subject_id: str, *, plan: dict, plan_id: str | None = None, enforce: bool = False,
                 acceptance_criteria: list | None = None, **kw):
        super().__init__(pool, subject_id, **kw)
        self.plan = plan
        self.plan_id = plan_id
        self.acceptance_criteria = list(acceptance_criteria or [])   # approved intake criteria (G3)
        self.by_stage: dict[str, str] = {}
        self.agent_of: dict[str, str] = {}
        self.state: dict[str, str] = {}
        # Plan-governed execution (OMNI_PLAN_DRIVEN=1): the durable task graph
        # admits every engine step; recording-only otherwise (legacy behaviour).
        self.enforce = enforce
        self.violation: str | None = None
        self.in_verification = False
        self.repair_rounds = 0
        self.verification_rounds = 0
        self.cost_source = None          # () -> {model task type: Decimal spent so far}
        self.charged: dict[str, Decimal] = {}
        tasks = {t.get('stage'): t for t in (plan or {}).get('tasks', []) if isinstance(t, dict)}
        self.max_repair_rounds = int((tasks.get('repair') or {}).get('max_iterations') or 0)
        self.model_task_stage = {t['model_task']: t['stage'] for t in tasks.values() if t.get('model_task')}

    # -------------------------------------------------- plan-governed execution
    def bind(self, engine, gateway) -> None:
        """Make the approved plan the source of the engine's limits and charge
        every model call to the plan task that made it."""
        if not self.enforce:
            return
        if getattr(engine, 'executor', None) is not None and not isinstance(engine.executor, PlanAdmittedExecutor):
            engine.executor = PlanAdmittedExecutor(engine.executor, self)
        if hasattr(engine, 'max_repair_rounds'):
            # The plan may only tighten the engine's own limit, never widen it.
            engine.max_repair_rounds = min(int(engine.max_repair_rounds), self.max_repair_rounds)
            self.max_repair_rounds = engine.max_repair_rounds
        recorder = getattr(gateway, 'recorder', None)

        def spent_by_task():
            out: dict[str, Decimal] = {}
            for r in getattr(recorder, 'records', None) or []:
                if getattr(r, 'kind', 'provider_call') != 'provider_call':
                    continue
                cost = r.metered_cost_usd if r.metered_cost_usd is not None else r.authorized_cost_usd
                out[r.task_type] = out.get(r.task_type, Decimal('0')) + Decimal(str(cost or 0))
            return out
        self.cost_source = spent_by_task

    def _violation(self, why: str):
        _log.warning('plan violation on %s: %s', self.subject_id, why)
        if self.violation is None:
            self.violation = why
        raise PlanViolation(why)

    def raise_if_violated(self) -> None:
        """Sticky: a violation swallowed by a caller (e.g. the QA reviewer turns
        any exception into 'reviewer unavailable') still fails the build."""
        if self.enforce and self.violation is not None:
            raise PlanViolation(self.violation)

    def _charge(self) -> None:
        """Charge new spend (metered, or the authorized worst case while unknown) to its plan task."""
        if self.cost_source is None:
            return
        for task_type, spent in self.cost_source().items():
            stage = self.model_task_stage.get(task_type) or MODEL_TASK_STAGE.get(task_type)
            tid = self.by_stage.get(stage)
            if tid is None:
                self._violation(f'model spend for {task_type!r}, which the plan does not contain')
            delta = spent - self.charged.get(tid, Decimal('0'))
            if delta > 0:
                try:
                    self.rt.charge(tid, delta, evidence={'charged_task_type': task_type})
                except RuntimeViolation as exc:
                    self._violation(f'{stage}: {exc}')
                self.charged[tid] = spent

    def _admit(self, stage: str) -> str:
        """The task of `stage` must be RUNNING, or move to RUNNING now (the runtime
        checks every dependency SUCCEEDED under a row lock)."""
        tid = self.by_stage.get(stage)
        if tid is None:
            self._violation(f'stage {stage!r} is not in the approved plan')
        st = self._last_state(tid)
        if st == 'RUNNING':
            return tid
        if st in ('PENDING', 'READY', 'REPAIRING'):
            try:
                self.rt.transition(tid, 'RUNNING')
            except RuntimeViolation as exc:
                self._violation(f'{stage} not admitted: {exc}')
            self.state[tid] = 'RUNNING'
            return tid
        self._violation(f'{stage} not admitted: task is {st}')

    def _finish_stage(self, stage: str, evidence: dict) -> None:
        tid = self.by_stage.get(stage)
        st = self._last_state(tid) if tid else None
        if st == 'RUNNING':
            try:
                self.rt.transition(tid, 'SUCCEEDED', evidence=evidence)
            except RuntimeViolation as exc:
                self._violation(f'{stage} could not complete: {exc}')
            self.state[tid] = 'SUCCEEDED'
            self.done[self.agent_of[tid]] = tid

    def on_check_start(self) -> None:
        if not self.enforce:
            return
        self.raise_if_violated()
        self._charge()
        self._finish_stage('codegen', {'note': 'files produced and handed to verification'})
        self._admit('unit_tests')
        self.verification_rounds += 1
        self.in_verification = True

    def _move(self, tid, target, evidence=None):
        if tid is None:
            return False
        ok = self._safe(self.rt.transition, tid, target, evidence=evidence or {}) is None and self._last_ok(tid, target)
        return ok

    def _last_ok(self, tid, target):
        try:
            st = self.rt.get(tid)['state']
        except Exception:
            return False
        self.state[tid] = st
        return st == target

    def start(self, *, from_brief: bool) -> None:
        def go():
            self.rt.supersede_open_runs(self.subject_kind, self.subject_id)
            self.run_id = self.rt.create_run(self.subject_kind, self.subject_id, budget_usd=self.budget)
            ids: dict[str, str] = {}
            from ..planning.graph import ExecutionGraph
            graph = ExecutionGraph.from_dict(self.plan)
            for plan_task_id in graph.order():
                t = graph.by_id[plan_task_id]
                tid = self.rt.add_task(self.run_id, t.responsible_agent, skills=t.required_skills,
                                       depends_on=[ids[x] for x in t.dependencies],
                                       budget_usd=t.maximum_authorized_cost_usd * t.max_iterations
                                       if t.maximum_authorized_cost_usd and t.model_task else None,
                                       evidence={'plan_task': t.task_id, 'plan_id': self.plan_id, 'stage': t.stage,
                                                 'department': t.department, 'task_type': t.task_type,
                                                 'conditional': t.conditional})
                ids[plan_task_id] = tid
                self.by_stage.setdefault(t.stage, tid)
                self.agent_of[tid] = t.responsible_agent
                if not t.executable:
                    self.rt.transition(tid, 'BLOCKED', evidence={'gap': t.gap or 'no execution engine'})
        self._safe(go)
        if self.enforce and (self.run_id is None or not self.by_stage):
            self._violation('the approved plan could not be materialized as durable tasks')
        for stage, note in (('intake', 'approved brief bound to the approval'), ('planning', 'build contract + reserved quote')):
            tid = self.by_stage.get(stage)
            if tid and self._move(tid, 'RUNNING'):
                self._move(tid, 'SUCCEEDED', {'source': note})
                self.done[self.agent_of[tid]] = tid

    def _stage_state(self, stage):
        tid = self.by_stage.get(stage)
        return tid, (self.state.get(tid) if tid else None)

    def _open(self, stage):
        tid, st = self._stage_state(stage)
        if tid is None:
            return None
        if st in (None, 'PENDING', 'READY'):
            self._move(tid, 'RUNNING')
        elif st == 'REPAIRING':
            self._move(tid, 'RUNNING')
        return tid

    def _close(self, stage, ok: bool, evidence=None):
        tid, st = self._stage_state(stage)
        if tid is None or st in ('SUCCEEDED', 'FAILED', 'CANCELLED', 'BLOCKED'):
            return
        if st != 'RUNNING' and not self._move(tid, 'RUNNING'):
            return
        if self._move(tid, 'SUCCEEDED' if ok else 'FAILED', evidence or {}) and ok:
            self.done[self.agent_of[tid]] = tid

    def on_model(self, task: str) -> None:
        if self.enforce:
            self._on_model_enforced(task)
            return
        stage = MODEL_TASK_STAGE.get(task)
        if stage is None:
            return
        if stage == 'codegen':
            self._close('architecture', True, {'note': 'spec produced; code generation started'})
        if stage in ('codegen', 'repair', 'review', 'architecture'):
            self._open(stage)

    def _on_model_enforced(self, task: str) -> None:
        self.raise_if_violated()
        self._charge()
        stage = self.model_task_stage.get(task) or MODEL_TASK_STAGE.get(task)
        if stage is None:
            self._violation(f'model call for {task!r}, which the plan does not contain')
        if stage == 'review':
            # The QA review runs inside an admitted verification run (its outcome
            # is decided later by the release policy); never on its own.
            if not self.in_verification:
                self._violation('review outside an admitted verification run')
            return
        if stage == 'codegen':
            arch = self.by_stage.get('architecture')
            if arch is not None and self._last_state(arch) == 'READY':
                self._admit('architecture')      # spec produced without a model call (deterministic floor)
            self._finish_stage('architecture', {'note': 'spec produced; code generation started'})
        if stage == 'repair':
            tid_u = self.by_stage.get('unit_tests')
            if tid_u is None or self._last_state(tid_u) != 'REPAIRING':
                self._violation('repair without a failed verification run')
            tid_r = self.by_stage.get('repair')
            if self._last_state(tid_r) != 'RUNNING':
                self.repair_rounds += 1
            if self.repair_rounds > self.max_repair_rounds:
                self._violation(f'repair round {self.repair_rounds} exceeds the plan limit {self.max_repair_rounds}')
        self._admit(stage)

    def on_check(self, passed: bool, summary: str) -> None:
        if self.enforce:
            self.raise_if_violated()
            self._charge()
            self.in_verification = False
            tid = self.by_stage.get('unit_tests')
            if passed:
                self._finish_stage('unit_tests', {'summary': summary[:300], 'tests_written_by': 'coding_agent'})
                self._finish_stage('repair', {'note': 'checks pass after repair'})
            else:
                self._move(tid, 'REPAIRING', {'last_failure': summary[:300]})
                tid_r = self.by_stage.get('repair')
                if self._last_state(tid_r) == 'RUNNING':     # next repair round re-admits explicitly
                    self._move(tid_r, 'REPAIRING', {'round': self.repair_rounds, 'last_failure': summary[:300]})
            return
        self._close('codegen', True, {'note': 'files produced and handed to verification'})
        tid = self._open('unit_tests')
        if tid is None:
            return
        if passed:
            self._close('unit_tests', True, {'summary': summary[:300], 'tests_written_by': 'coding_agent'})
            tid_r, st_r = self._stage_state('repair')
            if st_r == 'RUNNING':
                self._close('repair', True, {'note': 'checks pass after repair'})
        else:
            self._move(tid, 'REPAIRING', {'last_failure': summary[:300]})

    def finish(self, *, status: str, evidence: dict | None) -> None:
        if self.run_id is None:
            return
        ev = evidence or {}
        qr = ev.get('quality_report') or {}
        checks = {c.get('check'): c.get('status') for c in qr.get('checks') or []}
        ready = status == 'ready'
        tid, st = self._stage_state('unit_tests')
        if st in ('RUNNING', 'REPAIRING'):
            if st == 'REPAIRING':
                self._move(tid, 'FAILED', {'note': 'checks still failing at the end of the build'})
            else:
                self._close('unit_tests', ready)
        tid, st = self._stage_state('repair')
        if st == 'RUNNING':
            self._close('repair', ready, {'note': 'build ' + status})
        for stage, check in STAGE_CHECK.items():
            res = checks.get(check)
            if res in ('PASS', 'FAIL'):
                self._close(stage, res == 'PASS', {'release_check': check, 'status': res})
        settlement = ev.get('economics_settlement') or {}
        if settlement:
            basis = (settlement.get('cost_basis') or {}).get('llm') or ''
            self._close('cost', not str(basis).startswith('UNKNOWN'), {'basis': str(basis)[:200]})
        if qr:
            gate_ok = ready and qr.get('decision') == 'READY'
            self._close('quality_gate', gate_ok, {'policy': qr.get('policy_version'), 'decision': qr.get('decision'),
                                                  'blocking': qr.get('blocking')})
            gtid, gst = self._stage_state('quality_gate')
            if gate_ok and gst == 'SUCCEEDED':
                for agent in ('coding_agent', 'repair_agent', 'behavioral_acceptance_agent', 'browser_rehearsal_agent',
                              'security_agent', 'cost_economics_agent', 'qa_agent'):
                    if agent in self.done:
                        self._safe(self.rt.verify, self.done[agent], gtid)
        if ready:
            self._close('release', True, {'note': 'version committed'})
        # Everything not reached ends CANCELLED (never silently SUCCEEDED).
        for stage, tid in self.by_stage.items():
            st = self._last_state(tid)
            if st in ('PENDING', 'READY'):
                self._move(tid, 'CANCELLED', {'note': 'not needed' if stage == 'repair' else f'not reached (build {status})'})
            elif st == 'BLOCKED':
                self._move(tid, 'CANCELLED', {'note': f'blocked; build {status}'})
            elif st in ('RUNNING', 'REPAIRING', 'VERIFYING'):
                self._move(tid, 'FAILED', {'note': f'interrupted: build {status}'})
        self._safe(self.rt.finish_run, self.run_id, status)

    def _last_state(self, tid):
        try:
            st = self.rt.get(tid)['state']
        except Exception:
            return None
        self.state[tid] = st
        return st


def recorder_for(pool, build_id: str, plan_binding: dict | None, *, enforce: bool = False):
    """The plan-bound recorder when the build carries an approved plan; the
    reactive recorder otherwise (legacy builds keep their behaviour).

    enforce=True (OMNI_PLAN_DRIVEN=1) makes the approved plan govern the build:
    every engine step must be admitted by the durable task graph and every
    model call is charged to its plan task's budget. Builds without a plan are
    unaffected (backward compatible); unsetting the flag is the rollback."""
    if plan_binding and isinstance(plan_binding.get('graph'), dict):
        return PlanBoundRecorder(pool, build_id, plan=plan_binding['graph'], plan_id=plan_binding.get('plan_id'),
                                 enforce=enforce, acceptance_criteria=plan_binding.get('acceptance_criteria'))
    return BuildAgentRecorder(pool, build_id)
