"""#85 propagation, with the REAL behaviour validator (Matt's HOLD, 2026-10-20).

The guard in test_round_preflight uses StaticChain, which calls pf.plan_coverage_gaps -- the very detector #85
changed. Here nothing of the round pre-flight is used to judge the outcome:

* chain   = the VerificationGroup of the production composition `investor_app._verification_executor()` (preview,
            behaviour, browser, visual; the outer quality-score wrapper is left out: it scores repo hygiene) with the real RemoteSandboxRepositoryExecutor._run (validate_snapshot, validate_command,
            JSON body, HMAC). Only two things are substituted:
              - threshold `execute()` (sandbox build/verify) -> controlled PASS;
              - the HTTP transport -> tests.test_sandbox_callers_real_policy.StubRunner, which re-validates the request
                like sandbox_service and, for the default profile, RUNS the argv in a subprocess: the shipped
                web_saas_acceptance.py runner starts the fixture app and judges the plan. The browser profile
                (Chromium) gets a canned clean report. This is a LOCAL PROCESS ADAPTER, not live sandbox evidence.
* plan    = every acceptance id covered by other steps, one step (s6) with acceptance_ids = [] (run 39377332673, S5).
* repair  = the narrow pre-flight call (a) returns no patch, (b) returns a still-invalid plan, (c) raises; a control
            (d) returns a valid plan. Real repair rounds touch only notes.txt (the plan stays invalid).

`python -m tests.test_preflight_propagation_real_behaviour` prints one raw line per case (used for BASE vs HEAD).
"""
import json
import os
import unittest
from unittest import mock

from tests.test_behavior_acceptance_in_build import NO_LOGIN_SCOPE, SPEC, repository
from tests.test_sandbox_callers_real_policy import StubRunner

INVALID_STEP = {"id": "s6", "kind": "api_smoke", "acceptance_ids": [], "method": "GET", "path": "/", "expect_status": 200}
ENV = {'OMNI_SANDBOX_RUNNER_URL': 'http://sandbox.invalid', 'OMNI_SANDBOX_SHARED_SECRET': 'x' * 40,
       'OMNI_CONSISTENCY_GATE': '0', 'OMNI_MIN_QUALITY_SCORE': '0'}


def base_repo():
    repo = repository(bug=False)
    # the preview smoke refuses placeholder pages (< 400 chars): give the fixture a real interface
    small = '<h1>Bookings</h1><form><input name=n><button>Add</button></form>'
    rows = ''.join(f'<tr><td>booking {i}</td><td>2026-10-{i:02d}</td><td><button>cancel</button></td></tr>' for i in range(1, 9))
    repo['app.py'] = repo['app.py'].replace(small, small + '<table><tr><th>name</th><th>date</th><th></th></tr>' + rows + '</table>')
    return repo


def with_plan(repo, extra_steps):
    manifest = json.loads(repo['.omni/project.json'])
    steps = manifest['web_saas_acceptance']['personas'][0]['steps']
    manifest['web_saas_acceptance']['personas'][0]['steps'] = [s for s in steps if s['id'] != 's6'] + list(extra_steps)
    return {**repo, '.omni/project.json': json.dumps(manifest)}


VALID = base_repo()
INVALID = with_plan(VALID, [INVALID_STEP])
STILL_INVALID = with_plan(VALID, [dict(INVALID_STEP, path='/?still-invalid')])


class Architect:
    def create_spec(self, prompt):
        return SPEC


class Generator:
    def generate(self, spec):
        from omni_prod.repository_patch import FilePatch
        return tuple(FilePatch(p, c) for p, c in INVALID.items())


class Repairer:
    def __init__(self, mode):
        self.mode, self.preflight_calls, self.round_calls = mode, 0, 0

    def repair(self, *, spec, repo_summary, failures):
        from omni_prod.repository_patch import FilePatch
        if any(str(f.get('message', '')).startswith('behavioural acceptance plan incomplete') for f in failures):
            self.preflight_calls += 1
            if self.mode == 'no_patch':
                return ()
            if self.mode == 'still_invalid':
                return (FilePatch('.omni/project.json', STILL_INVALID['.omni/project.json']),)
            if self.mode == 'raises':
                raise RuntimeError('ordinary repair error')
            return (FilePatch('.omni/project.json', VALID['.omni/project.json']),)       # control
        self.round_calls += 1
        return (FilePatch('notes.txt', f'round {self.round_calls}'),)                     # the plan stays as it is


def run_case(mode, max_repair_rounds=1):
    from omni_prod import investor_app
    from omni_prod.autonomous_core import AutonomousProductEngine, ExecutionReport
    from omni_prod.behavior_acceptance import BehaviorAcceptanceExecutor, find_in_chain
    from omni_prod.remote_sandbox import RemoteSandboxRepositoryExecutor
    runner = StubRunner()

    class Remote(RemoteSandboxRepositoryExecutor):
        def __init__(self, config, **_):
            super().__init__(config, urlopen=runner)

        def execute(self, *, repository, spec):
            return ExecutionReport(True, (), 'threshold: controlled PASS')

    reports = []
    with mock.patch.dict(os.environ, ENV), mock.patch.object(investor_app, 'RemoteSandboxRepositoryExecutor', Remote):
        from omni_prod.quality_gate import QualityAwareExecutor
        from omni_prod.verification_group import VerificationGroup
        production = investor_app._verification_executor(None)
        # The aggregation under test is the VerificationGroup; the outer quality score (repo hygiene: README, CI,
        # locales) is a separate gate and would fail this minimal fixture whatever the plan.
        assert isinstance(production, QualityAwareExecutor) and isinstance(production._inner, VerificationGroup)
        executor = production._inner
        find_in_chain(executor, BehaviorAcceptanceExecutor).scope = NO_LOGIN_SCOPE
        real_execute = executor.execute

        def record(*, repository, spec):
            r = real_execute(repository=repository, spec=spec)
            reports.append(r)
            return r
        executor.execute = record
        repairer = Repairer(mode)
        engine = AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=repairer,
                                         executor=executor, max_repair_rounds=max_repair_rounds)
        result = engine.build('bookings')
    behaviour = [r for r in runner.requests if r['build_id'] == 'behavior-acceptance']
    first = behaviour[0] if behaviour else None
    sent_plan = json.loads(first['repository']['.omni/project.json'])['web_saas_acceptance'] if first else None
    pre = [e for e in engine.failure_taxonomy if e['layer'] == 'preflight']
    return {
        'mode': mode,
        'behaviour_requests': len(behaviour),
        'first_behaviour_plan_has_s6_without_ids': bool(sent_plan) and any(
            s['id'] == 's6' and not s.get('acceptance_ids') for s in sent_plan['personas'][0]['steps']),
        'first_aggregate_passed': reports[0].passed if reports else None,
        'first_behaviour_failure': next((f.message for f in (reports[0].failures if reports else ())
                                         if f.acceptance_id == 'BEHAVIOR'), None),
        'status': result.status, 'repair_rounds': result.repair_rounds,
        'preflight_calls': repairer.preflight_calls,
        'was_repaired': [e['was_repaired'] for e in pre],
    }


FAILING_MODES = ('no_patch', 'still_invalid', 'raises')


class PreflightFallbackReachesTheRealBehaviourCheck(unittest.TestCase):
    """HEAD expectations (#85). On BASE the control differs: no pre-flight call, one counted round."""

    @classmethod
    def setUpClass(cls):
        cls.out = {m: run_case(m) for m in (*FAILING_MODES, 'valid_fix')}

    def test_an_unresolved_plan_reaches_behaviour_as_it_is_and_costs_a_real_round(self):
        for mode in FAILING_MODES:
            o = self.out[mode]
            self.assertGreaterEqual(o['behaviour_requests'], 1, o)                  # behaviour really ran
            self.assertTrue(o['first_behaviour_plan_has_s6_without_ids'], o)        # the plan, unchanged
            self.assertIs(o['first_aggregate_passed'], False, o)
            self.assertIn('step s6 must reference contract acceptance_ids', o['first_behaviour_failure'] or '', o)
            self.assertEqual(o['status'], 'failed', o)
            self.assertGreaterEqual(o['repair_rounds'], 1, o)
            self.assertEqual(o['preflight_calls'] >= 1, True, o)                     # the narrow fix was tried
            self.assertNotIn(True, o['was_repaired'], o)

    def test_control_a_valid_narrow_fix_passes_with_zero_counted_rounds(self):
        o = self.out['valid_fix']
        self.assertEqual((o['status'], o['repair_rounds']), ('ready', 0), o)
        self.assertIs(o['first_aggregate_passed'], True, o)
        self.assertFalse(o['first_behaviour_plan_has_s6_without_ids'], o)
        self.assertGreaterEqual(o['behaviour_requests'], 1, o)
        self.assertEqual(o['was_repaired'], [True], o)


if __name__ == '__main__':
    for m in (*FAILING_MODES, 'valid_fix'):
        print('PROPAGATION ' + json.dumps(run_case(m), ensure_ascii=False))
