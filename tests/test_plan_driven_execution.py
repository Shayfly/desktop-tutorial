"""Plan-governed execution (OMNI_PLAN_DRIVEN=1, ADWv1 gap G1).

The Chief Architect's approved ExecutionGraph, materialized as durable
agent_tasks rows, ADMITS every step of the existing engine: a model call or a
verification run whose plan task is not READY/RUNNING (dependencies not
SUCCEEDED under a row lock) stops the build with PlanViolation; every model
call is charged to its plan task's budget; the plan's repair limit bounds the
engine. Legacy (recording-only) behaviour is unchanged without the flag.

The live tests run against a REAL PostgreSQL (M4D2_DATABASE_URL, schema through
migration 036) and are skipped -- not faked -- without one. No model provider
is called: the engine's agents are local stubs that go through the same
BuildControl hooks the routed gateway uses (before_call), and their spend is
written as attempt records exactly like the gateway's recorder.
"""
import copy
import os
import unittest
import uuid
from decimal import Decimal
from types import SimpleNamespace

from omni_prod.attempt_ledger import AttemptRecord
from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.build_control import BuildControl, install as install_build_control
from omni_prod.intake import contract as C
from omni_prod.planning.architect import ChiefArchitect
from omni_prod.repository_patch import parse_patch

from tests.test_conversation_os import _live_skip, complete_brief, DATABASE_URL


def plan_graph(**repair_overrides):
    graph = copy.deepcopy(ChiefArchitect().plan(C.build(complete_brief()))['execution_graph'])
    for t in graph['tasks']:
        if t['stage'] == 'repair':
            t.update(repair_overrides)
    return graph


class Gateway:
    """The two attributes of RoutedModelGateway the plan uses: before_call and recorder.records."""

    def __init__(self):
        self.before_call = None
        self.recorder = SimpleNamespace(records=[])

    def call(self, task: str, cost: str = '0.01', *, metered: bool = True):
        self.before_call(task)                          # admission happens BEFORE the provider is contacted
        c = Decimal(cost)
        self.recorder.records.append(AttemptRecord(task_type=task, attempt_seq=len(self.recorder.records),
                                                   kind='provider_call', outcome='ok',
                                                   authorized_cost_usd=c, metered_cost_usd=c if metered else None))


class Arch:
    def __init__(self, gw, cost='0.01'):
        self.gw, self.cost = gw, cost

    def create_spec(self, prompt):
        self.gw.call('architecture', self.cost)
        return 'spec'


class Gen:
    def __init__(self, gw, cost='0.05'):
        self.gw, self.cost = gw, cost

    def generate(self, spec):
        self.gw.call('codegen', self.cost)
        return parse_patch({'files': [{'path': 'app.py', 'content': 'v0'}]})


class Rep:
    def __init__(self, gw, cost='0.01'):
        self.gw, self.cost, self.n = gw, cost, 0

    def repair(self, **kw):
        self.n += 1
        self.gw.call('repair', self.cost)
        return parse_patch({'files': [{'path': 'app.py', 'content': f'v{self.n}'}]})


class Exec:
    """Fails the first `fail_first` runs; runs the QA review inside each run."""

    def __init__(self, gw, fail_first=0, review=True, inner=None):
        self.gw, self.fail_first, self.review, self.inner, self.runs = gw, fail_first, review, inner, 0

    def execute(self, *, repository, spec):
        self.runs += 1
        if self.review:
            self.gw.call('review', '0.005')
        if self.inner:
            self.inner()
        if self.runs <= self.fail_first:
            return ExecutionReport(False, (AcceptanceFailure('BEHAVIOR', f'run {self.runs} failed'),))
        return ExecutionReport(True)


def _not_live():
    return _live_skip()


@unittest.skipIf(_not_live(), _not_live())
class PlanGovernedBuildTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.agent_os.runtime import AgentRuntime
        from omni_prod.db import DatabasePool
        self.pool = DatabasePool(DATABASE_URL)
        self.rt = AgentRuntime(self.pool)

    def tearDown(self):
        getattr(self.pool, 'close', lambda: None)()

    def recorder(self, graph=None, *, enforce=True, build_id=None):
        from omni_prod.agent_os.recorder import recorder_for
        return recorder_for(self.pool, build_id or f'bld_{uuid.uuid4().hex}',
                            {'graph': graph or plan_graph(), 'plan_id': 'pln_test'}, enforce=enforce)

    def engine(self, rec, *, fail_first=0, max_repair_rounds=3, gen_cost='0.05', review=True, inner=None):
        gw = Gateway()
        engine = AutonomousProductEngine(architect=Arch(gw), generator=Gen(gw, gen_cost), repairer=Rep(gw),
                                         executor=Exec(gw, fail_first, review, inner), max_repair_rounds=max_repair_rounds)
        control = BuildControl(SimpleNamespace(), 'bld_x')
        install_build_control(engine, gw, control)
        control.recorder = rec
        rec.start(from_brief=True)
        rec.bind(engine, gw)
        return engine, gw

    def tasks(self, rec):
        return {t['evidence']['plan_task']: t for t in self.rt.tasks(rec.run_id)}

    # ---------------------------------------------------------------- happy path
    def test_plan_admits_the_real_engine_in_dependency_order_and_charges_each_task(self):
        rec = self.recorder()
        engine, gw = self.engine(rec, fail_first=1)
        result = engine.build('p')
        self.assertEqual(result.status, 'ready')
        t = self.tasks(rec)
        for pid in ('T01', 'T02', 'T03', 'T04', 'T05', 'T06'):
            self.assertEqual(t[pid]['state'], 'SUCCEEDED', pid)
        # Order proven by the durable timestamps, not by the recorder's memory.
        with self.pool.connection() as conn:
            ts = {r[0]: (r[1], r[2]) for r in conn.execute(
                "SELECT evidence->>'plan_task', started_at, finished_at FROM agent_tasks WHERE run_id = %s",
                (rec.run_id,)).fetchall()}
        self.assertLess(ts['T03'][0], ts['T04'][0])
        self.assertLessEqual(ts['T03'][1], ts['T04'][0])
        self.assertLessEqual(ts['T04'][1], ts['T05'][0])
        # Every model call charged to its own plan task (metered cost).
        self.assertEqual(Decimal(str(t['T03']['cost_usd'])), Decimal('0.01'))
        self.assertEqual(Decimal(str(t['T04']['cost_usd'])), Decimal('0.05'))
        self.assertEqual(Decimal(str(t['T06']['cost_usd'])), Decimal('0.01'))
        self.assertEqual(Decimal(str(t['T15']['cost_usd'])), Decimal('0.010'))      # two review runs x 0.005
        self.assertEqual(rec.repair_rounds, 1)
        self.assertEqual(rec.verification_rounds, 2)
        self.assertIsNone(rec.violation)

    def test_unknown_cost_is_charged_at_the_authorized_worst_case(self):
        rec = self.recorder()
        engine, gw = self.engine(rec)
        orig = gw.call
        gw.call = lambda task, cost='0.01', metered=True: orig(task, cost, metered=task != 'codegen')
        engine.build('p')
        self.assertEqual(Decimal(str(self.tasks(rec)['T04']['cost_usd'])), Decimal('0.05'))

    # ------------------------------------------------------------ repair limits
    def test_plan_repair_limit_lower_than_the_engine_bounds_the_engine(self):
        rec = self.recorder(plan_graph(max_iterations=1))
        engine, gw = self.engine(rec, fail_first=10, max_repair_rounds=3)
        self.assertEqual(engine.max_repair_rounds, 1)
        result = engine.build('p')
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.repair_rounds, 1)
        self.assertEqual(engine.repairer.n, 1)

    def test_plan_never_widens_the_engine_limit(self):
        rec = self.recorder(plan_graph(max_iterations=5))
        engine, gw = self.engine(rec, max_repair_rounds=2)
        self.assertEqual(engine.max_repair_rounds, 2)
        self.assertEqual(rec.max_repair_rounds, 2)

    def test_repair_round_over_the_plan_limit_is_refused_before_the_provider(self):
        rec = self.recorder(plan_graph(max_iterations=1))
        rec.start(from_brief=True)
        from omni_prod.agent_os.recorder import PlanViolation
        rec.on_model('architecture'); rec.on_model('codegen')
        rec.on_check_start(); rec.on_check(False, 'f1')
        rec.on_model('repair')
        rec.on_check_start(); rec.on_check(False, 'f2')
        with self.assertRaises(PlanViolation):
            rec.on_model('repair')
        self.assertIn('exceeds the plan limit 1', rec.violation)

    # -------------------------------------------------------------- violations
    def test_out_of_order_steps_are_refused(self):
        from omni_prod.agent_os.recorder import PlanViolation
        rec = self.recorder(); rec.start(from_brief=True)
        with self.assertRaises(PlanViolation):
            rec.on_model('repair')                      # nothing has failed yet
        rec2 = self.recorder(); rec2.start(from_brief=True)
        with self.assertRaises(PlanViolation):
            rec2.on_check_start()                       # verification before any code exists
        self.assertEqual(self.tasks(rec2)['T05']['state'], 'PENDING')

    def test_a_completed_step_cannot_run_twice(self):
        from omni_prod.agent_os.recorder import PlanViolation
        rec = self.recorder(); rec.start(from_brief=True)
        rec.on_model('architecture'); rec.on_model('codegen')
        with self.assertRaises(PlanViolation):
            rec.on_model('architecture')                # SUCCEEDED: a second architecture run is double execution
        with self.assertRaises(PlanViolation):
            rec.on_check_start()                        # sticky: nothing runs after a violation
        rec2 = self.recorder(); rec2.start(from_brief=True)
        rec2.on_model('architecture'); rec2.on_model('codegen'); rec2.on_check_start(); rec2.on_check(True, 'ok')
        with self.assertRaises(PlanViolation):
            rec2.on_model('codegen')

    def test_task_budget_exceeded_blocks_the_task_and_fails_the_build(self):
        from omni_prod.agent_os.recorder import PlanViolation
        rec = self.recorder()
        engine, gw = self.engine(rec, gen_cost='0.25')        # plan cap for T04 is 0.20
        with self.assertRaises(PlanViolation):
            engine.build('p')
        t = self.tasks(rec)['T04']
        self.assertEqual(t['state'], 'BLOCKED')
        self.assertIn('budget', t['evidence']['blocked'])
        from omni_prod.behavior_acceptance import find_in_chain
        self.assertEqual(find_in_chain(engine.executor, Exec).runs, 0)   # verification never started

    def test_review_only_inside_an_admitted_verification_run(self):
        from omni_prod.agent_os.recorder import PlanViolation
        rec = self.recorder(); rec.start(from_brief=True)
        rec.on_model('architecture'); rec.on_model('codegen')
        with self.assertRaises(PlanViolation):
            rec.on_model('review')

    def test_a_violation_swallowed_by_a_caller_still_fails_the_build(self):
        from omni_prod.agent_os.recorder import PlanViolation
        rec = self.recorder()
        holder = {}

        def swallowing_reviewer():          # product_review turns any exception into "reviewer unavailable"
            try:
                holder['gw'].call('modification')
            except Exception:
                pass
        engine, gw = self.engine(rec, review=False, inner=swallowing_reviewer)
        holder['gw'] = gw
        with self.assertRaises(PlanViolation):
            engine.build('p')
        self.assertIn('modification', rec.violation)

    def test_unmaterializable_plan_fails_closed(self):
        from omni_prod.agent_os.recorder import PlanBoundRecorder, PlanViolation
        rec = PlanBoundRecorder(self.pool, f'bld_{uuid.uuid4().hex}', plan={'tasks': [{'bogus': 1}], 'budget_usd': '1'},
                                enforce=True)
        with self.assertRaises(PlanViolation):
            rec.start(from_brief=True)

    def test_a_superseded_worker_cannot_continue(self):
        """No double execution: a recovered build supersedes the lost worker's
        run; if that worker is still alive, its next step is refused."""
        from omni_prod.agent_os.recorder import PlanViolation
        build_id = f'bld_{uuid.uuid4().hex}'
        old = self.recorder(build_id=build_id); old.start(from_brief=True)
        old.on_model('architecture'); old.on_model('codegen')
        new = self.recorder(build_id=build_id); new.start(from_brief=True)
        self.assertEqual(self.tasks(old)['T04']['state'], 'FAILED')
        with self.assertRaises(PlanViolation):
            old.on_check_start()
        with self.assertRaises(PlanViolation):
            old.on_model('codegen')
        new.on_model('architecture'); new.on_model('codegen'); new.on_check_start(); new.on_check(True, 'ok')
        self.assertEqual(self.tasks(new)['T05']['state'], 'SUCCEEDED')

    def test_finish_after_plan_governed_build_closes_every_task(self):
        rec = self.recorder()
        engine, gw = self.engine(rec)
        engine.build('p')
        checks = [{'check': c, 'status': 'PASS'} for c in ('preview_starts', 'behavioural_acceptance', 'browser_flow',
                                                           'visual_layout_desktop_mobile', 'static_security_scan',
                                                           'qa_review_blocking_findings')]
        rec.finish(status='ready', evidence={'quality_report': {'decision': 'READY', 'checks': checks},
                                             'economics_settlement': {'cost_basis': {'llm': 'metered'}}})
        st = {k: v['state'] for k, v in self.tasks(rec).items()}
        self.assertEqual(st.pop('T06'), 'CANCELLED')          # repair not needed
        self.assertEqual(set(st.values()), {'SUCCEEDED'})

    # ---------------------------------------------------------- compatibility
    def test_without_the_flag_the_recorder_only_records(self):
        rec = self.recorder(enforce=False)
        engine, gw = self.engine(rec, gen_cost='0.25', fail_first=1)   # over budget, would violate if enforced
        self.assertEqual(engine.max_repair_rounds, 3)                 # plan does not touch the engine
        result = engine.build('p')
        self.assertEqual(result.status, 'ready')
        self.assertEqual(Decimal(str(self.tasks(rec)['T04']['cost_usd'])), Decimal('0'))
        rec.on_model('architecture')                                  # out of order: recorded, not refused


class WiringTests(unittest.TestCase):
    def test_failure_code(self):
        from omni_prod.agent_os.recorder import PlanViolation
        from omni_prod.worker_tasks import failure_code
        self.assertEqual(failure_code(PlanViolation('x')), 'plan_violation')
        self.assertEqual(failure_code(RuntimeError('x')), 'worker_exception')

    def test_recorder_for_keeps_legacy_builds_reactive(self):
        from omni_prod.agent_os.recorder import BuildAgentRecorder, PlanBoundRecorder, recorder_for
        pool = object()
        legacy = recorder_for(pool, 'bld_1', None, enforce=True)
        self.assertIs(type(legacy), BuildAgentRecorder)               # no plan: the flag changes nothing
        planned = recorder_for(pool, 'bld_1', {'graph': {'tasks': []}}, enforce=True)
        self.assertIsInstance(planned, PlanBoundRecorder)
        self.assertTrue(planned.enforce)
        self.assertFalse(recorder_for(pool, 'bld_1', {'graph': {'tasks': []}}).enforce)

    def test_bind_wraps_the_executor_once_and_keeps_the_chain_reachable(self):
        from omni_prod.agent_os.recorder import PlanAdmittedExecutor, PlanBoundRecorder
        from omni_prod.behavior_acceptance import find_in_chain
        inner = Exec(Gateway())
        engine = SimpleNamespace(executor=inner, max_repair_rounds=3)
        rec = PlanBoundRecorder(object(), 'bld_1', plan=plan_graph(), enforce=True)
        rec.bind(engine, Gateway()); rec.bind(engine, Gateway())
        self.assertIsInstance(engine.executor, PlanAdmittedExecutor)
        self.assertIs(engine.executor._inner, inner)                  # wrapped exactly once
        self.assertIs(find_in_chain(engine.executor, Exec), inner)
        legacy = SimpleNamespace(executor=inner, max_repair_rounds=3)
        PlanBoundRecorder(object(), 'bld_1', plan=plan_graph()).bind(legacy, Gateway())
        self.assertIs(legacy.executor, inner)                         # flag off: untouched

    def test_worker_reads_the_flag_and_binds_the_plan(self):
        import inspect
        from omni_prod import worker_tasks as W
        src = inspect.getsource(W)
        self.assertIn("enforce=os.getenv('OMNI_PLAN_DRIVEN') == '1'", src)
        body = inspect.getsource(W._run_live_build_job)
        self.assertLess(body.index('agent_recorder.start('), body.index('agent_recorder.bind(engine, gateway)'))
        self.assertLess(body.index('agent_recorder.bind(engine, gateway)'), body.index('engine.build(prompt)'))
        self.assertLess(body.index('engine.build(prompt)'), body.index('agent_recorder.raise_if_violated()'))



def model_spec():
    from omni_prod.product_spec import ProductSpec
    return ProductSpec.from_dict({'title': 'Loans', 'summary': 'Track loans', 'stack': ['python'],
                                  'requirements': [{'id': 'R1', 'text': 'list loans'}],
                                  'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'loans are listed'}]})


APPROVED = [{'id': 'AC1', 'covers': 'F1', 'given_when_then': 'Given the product is open, when the user adds a loan, then it persists'},
            {'id': 'AC2', 'covers': 'F2', 'given_when_then': 'Verified: overdue loans are highlighted'}]


class ApprovedCriteriaTests(unittest.TestCase):
    """ADWv1 G3: approved criteria -> spec -> behavioural coverage -> mandatory release check."""

    def test_plan_carries_the_approved_criteria(self):
        plan = ChiefArchitect().plan(C.build(complete_brief()))
        ids = [a['id'] for a in plan['acceptance_criteria']]
        self.assertTrue(ids and ids[0] == 'AC1')

    def test_merge_keeps_the_model_spec_and_adds_every_approved_criterion(self):
        from omni_prod.worker_tasks import merge_approved_criteria
        spec = merge_approved_criteria(model_spec(), APPROVED)
        self.assertEqual([a.id for a in spec.acceptance], ['A1', 'APPROVED-AC1', 'APPROVED-AC2'])
        self.assertIn('APPROVED-F1', {r.id for r in spec.requirements})
        self.assertEqual(merge_approved_criteria(spec, APPROVED), spec)          # idempotent
        with self.assertRaises(ValueError):
            merge_approved_criteria(model_spec(), [{'id': 'AC9'}])                # no silent empty criterion

    def test_architect_wrapper_is_installed_only_with_criteria(self):
        from omni_prod.worker_tasks import (ApprovedCriteriaArchitect, approved_criteria_evidence,
                                            install_approved_criteria)

        class Arch:
            def create_spec(self, prompt):
                return model_spec()
        engine = SimpleNamespace(architect=Arch())
        self.assertFalse(install_approved_criteria(engine, {'acceptance_criteria': []}))
        self.assertIsNone(approved_criteria_evidence(engine))
        self.assertTrue(install_approved_criteria(engine, {'acceptance_criteria': APPROVED}))
        install_approved_criteria(engine, {'acceptance_criteria': APPROVED})
        self.assertIsInstance(engine.architect, ApprovedCriteriaArchitect)
        self.assertNotIsInstance(engine.architect._inner, ApprovedCriteriaArchitect)   # once
        self.assertIn('APPROVED-AC2', [a.id for a in engine.architect.create_spec('p').acceptance])
        self.assertEqual(approved_criteria_evidence(engine)['ids'], ['APPROVED-AC1', 'APPROVED-AC2'])

    def _report(self, *, approved, covered=None, beh_status='PASS', spec=None):
        from omni_prod.release_policy import build_report
        from omni_prod.worker_tasks import merge_approved_criteria
        ok = SimpleNamespace(passed=True, score=90, minimum_score=80, publish_allowed=True, status='CLEAR')
        spec = spec or merge_approved_criteria(model_spec(), APPROVED)
        result = SimpleNamespace(status='ready', spec=spec, report=ExecutionReport(True))
        ev = {'approved_acceptance': approved}
        if covered is not None:
            ev['behavior_acceptance'] = {'last': {'status': beh_status, 'covered_acceptance_ids': covered}}
        r = build_report(build_id='b', artifact_sha256='0' * 64, result=result, evidence=ev,
                         quality=ok, security=ok, rights=ok)
        return {c.check: c for c in r.checks}['approved_criteria_covered'], r

    def test_release_check_statuses(self):
        ids = {'ids': ['APPROVED-AC1', 'APPROVED-AC2']}
        c, r = self._report(approved=ids, covered=['A1', 'APPROVED-AC1', 'APPROVED-AC2'])
        self.assertEqual((c.status, c.required), ('PASS', True))
        c, r = self._report(approved=ids, covered=['A1', 'APPROVED-AC1'])
        self.assertEqual(c.status, 'FAIL'); self.assertIn('APPROVED-AC2', c.detail)
        self.assertIn('acceptance/approved_criteria_covered: FAIL', r.to_dict()['blocking'])
        c, r = self._report(approved=ids)                                  # behaviour never ran
        self.assertEqual(c.status, 'NOT_RUN'); self.assertEqual(r.decision, 'FAILED')
        c, _ = self._report(approved=ids, covered=['APPROVED-AC1', 'APPROVED-AC2'], spec=model_spec())
        self.assertEqual(c.status, 'FAIL'); self.assertIn('missing from the spec', c.detail)
        c, _ = self._report(approved={'ids': []}, covered=[])
        self.assertEqual(c.status, 'FAIL')

    def test_legacy_builds_have_no_approved_check(self):
        from omni_prod.release_policy import build_report
        ok = SimpleNamespace(passed=True, score=90, minimum_score=80, publish_allowed=True, status='CLEAR')
        result = SimpleNamespace(status='ready', spec=model_spec(), report=ExecutionReport(True))
        r = build_report(build_id='b', artifact_sha256='0' * 64, result=result, evidence={}, quality=ok, security=ok, rights=ok)
        self.assertNotIn('approved_criteria_covered', {c.check for c in r.checks})

    def test_recorder_for_carries_the_criteria_and_the_worker_installs_them_only_when_enforced(self):
        import inspect
        from omni_prod import worker_tasks as W
        from omni_prod.agent_os.recorder import recorder_for
        rec = recorder_for(object(), 'b', {'graph': {'tasks': []}, 'acceptance_criteria': APPROVED}, enforce=True)
        self.assertEqual(rec.acceptance_criteria, APPROVED)
        body = inspect.getsource(W._run_live_build_job)
        i = body.index("if getattr(agent_recorder, 'enforce', False):")
        self.assertLess(i, body.index('install_approved_criteria(engine'))
        self.assertLess(body.index('install_approved_criteria(engine'), body.index('engine.build(prompt)'))


class PlanContentsTests(unittest.TestCase):
    """Master directive stage 2: the plan states I/O, permissions, budgets, tests,
    repair/escalation and the final deliverable + preview -- and it is the same
    graph that governs execution (tests above)."""

    def test_every_task_has_contracts_permissions_and_policies(self):
        plan = ChiefArchitect().plan(C.build(complete_brief()))
        for t in plan['execution_graph']['tasks']:
            for key in ('inputs', 'expected_outputs', 'acceptance_criteria', 'verification_strategy', 'retry_policy',
                        'failure_policy', 'rollback_policy', 'escalation_policy', 'responsible_agent', 'required_skills'):
                self.assertTrue(t[key], (t['task_id'], key))
            self.assertTrue(plan['permissions'][t['task_id']], t['task_id'])
        perms = plan['permissions']
        self.assertTrue(any('remote sandbox' in p for p in perms['T05']))
        self.assertTrue(any("'codegen'" in p and '0.20' in p for p in perms['T04']))
        self.assertIn('no model calls', perms['T01'])

    def test_deliverable_and_preview_are_defined_by_release_checks(self):
        plan = ChiefArchitect().plan(C.build(complete_brief()))
        prev = plan['deliverable']['preview']
        self.assertTrue(prev['required'])
        self.assertIn('approved_criteria_covered', prev['must_pass'])
        self.assertIn('private preview', ' '.join(plan['deliverable']['items']))
        self.assertIn('no parallel dispatch', plan['execution_mode']['not_yet'])

    def test_plan_additions_do_not_change_the_graph_fingerprint(self):
        from omni_prod.planning.graph import ExecutionGraph
        plan = ChiefArchitect().plan(C.build(complete_brief()))
        self.assertEqual(ExecutionGraph.from_dict(plan['execution_graph']).fingerprint(), plan['graph_fingerprint'])

if __name__ == '__main__':
    unittest.main()
