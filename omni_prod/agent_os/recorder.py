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
        tid = self.current[0] if self.current else None
        self._close_current('SUCCEEDED' if passed else 'FAILED', {'summary': summary[:300]})
        if passed and tid:
            producer = self.done.get('repair_agent') or self.done.get('coding_agent')
            if producer:
                self._safe(self.rt.verify, producer, tid)

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
            final.append(('cost_economics_agent', ('credit_settlement',), True, (settlement.get('cost_basis') or {}).get('llm')))
        if status == 'ready':
            final.append(('release_agent', ('version_create', 'release_gate'), True, 'version committed'))
        for agent, skills, ok, note in final:
            tid = self._safe(self.rt.add_task, self.run_id, agent, skills=skills)
            if tid:
                self._safe(self.rt.transition, tid, 'RUNNING')
                self._safe(self.rt.transition, tid, 'SUCCEEDED' if ok else 'FAILED', evidence={'note': str(note)[:200]})
                if ok:
                    self.done[agent] = tid
        gate = self._safe(self.rt.add_task, self.run_id, 'quality_gate_agent')
        if gate:
            self._safe(self.rt.transition, gate, 'RUNNING')
            self._safe(self.rt.transition, gate, 'SUCCEEDED' if status == 'ready' else 'FAILED', evidence={'status': status})
            if status == 'ready':
                for agent in ('release_agent', 'behavioral_acceptance_agent', 'browser_rehearsal_agent', 'security_agent',
                              'cost_economics_agent', 'qa_agent'):
                    if agent in self.done:
                        self._safe(self.rt.verify, self.done[agent], gate)
        self._safe(self.rt.finish_run, self.run_id, status)


__all__ = ['BuildAgentRecorder', 'RuntimeViolation']
