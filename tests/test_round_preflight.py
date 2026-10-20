"""Round pre-flight, review in the group, plan coverage before the round counts (2026-10-19).

Rehearsals 39295707756 / 39313029465: round 1 was spent on a syntax error in a generated test file (3 of 3 rehearsals)
and a round on a behaviour plan missing an acceptance id; the QA review ran only after everything else passed, in the
last round. Each test below fails on the old code and passes on the new one, except the two guards at the end, which
prove pre-flight never hides a real failure.
"""
import json
import unittest

from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.repository_patch import FilePatch
from omni_prod import round_preflight as pf

try:
    from tests.test_verification_group import PostBuildChecksReachTheRepairerTogether as _Chain, MANIFEST
except ImportError:  # pragma: no cover - the chain needs fastapi (present in CI)
    _Chain, MANIFEST = None, None

SPEC = type('S', (), {'acceptance': [type('A', (), {'id': 'A1', 'text': 'opens'})(), type('A', (), {'id': 'A2', 'text': 'adds'})()],
                      'requirements': []})()
PLAN_OK = {"schema_version": 2, "runtime": "python:3.11-slim", "start": ["python", "app.py"], "port": 8000,
           "health_path": "/", "web_saas_acceptance": {"product_family": "managed_web_saas_v1", "required_kinds": ["api_smoke"],
           "personas": [{"id": "v", "steps": [
               {"id": "s1", "kind": "api_smoke", "acceptance_ids": ["A1"], "method": "GET", "path": "/", "expect_status": 200},
               {"id": "s2", "kind": "data_create", "acceptance_ids": ["A2"], "method": "POST", "path": "/x", "expect_status": 201}]}]}}
PLAN_MISSING_A2 = json.loads(json.dumps(PLAN_OK))
PLAN_MISSING_A2['web_saas_acceptance']['personas'][0]['steps'].pop()
BROKEN_TEST = 'def test_x():\n    assert "unterminated\n'


class Architect:
    def create_spec(self, prompt):
        return SPEC


class Generator:
    def __init__(self, files):
        self.files = files

    def generate(self, spec):
        return tuple(FilePatch(p, c) for p, c in self.files.items())


class Repairer:
    """Fixes what it is asked to fix; records every call (pre-flight calls included)."""
    def __init__(self, can_fix=True, also_touch_app=False):
        self.calls, self.can_fix, self.also_touch_app = [], can_fix, also_touch_app

    def repair(self, *, spec, repo_summary, failures):
        self.calls.append([f['message'][:60] for f in failures])
        out = []
        for f in failures:
            if 'syntax' in f['message'] and self.can_fix:
                out.append(FilePatch('tests/test_app.py', 'def test_x():\n    assert True\n'))
            if 'plan incomplete' in f['message'] and self.can_fix:
                out.append(FilePatch('.omni/project.json', json.dumps(PLAN_OK)))
        if self.also_touch_app:
            out.append(FilePatch('app.py', 'print("rewritten by a pre-flight call")\n'))
        out.append(FilePatch('notes.txt', f'repair {len(self.calls)}'))   # every call changes something
        return tuple(out)


class StaticChain:
    """Stands in for the chain: consistency (syntax) then the runner's plan-coverage check, then pass."""
    def __init__(self):
        self.runs = []

    def execute(self, *, repository, spec):
        self.runs.append(dict(repository))
        if pf.syntax_errors(repository):
            return ExecutionReport(False, (AcceptanceFailure('CONSISTENCY', 'consistency (syntax): broken file'),))
        if pf.plan_coverage_gaps(repository, spec):
            return ExecutionReport(False, (AcceptanceFailure('BEHAVIOR', 'behavioural acceptance failed: missing acceptance coverage'),))
        return ExecutionReport(True, ())


def build(files, repairer):
    chain = StaticChain()
    engine = AutonomousProductEngine(architect=Architect(), generator=Generator(files), repairer=repairer,
                                     executor=chain, max_repair_rounds=3)
    return engine, engine.build('league'), chain


BASE = {'app.py': 'print("ok")\n', '.omni/project.json': json.dumps(PLAN_OK)}


class PreflightGivesTheRoundBack(unittest.TestCase):
    def test_a_syntax_error_is_fixed_before_the_chain_and_costs_no_round(self):
        engine, result, chain = build({**BASE, 'tests/test_app.py': BROKEN_TEST}, Repairer())
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0))
        self.assertEqual(len(chain.runs), 1)                                   # the chain ran once, on the fixed repo
        events = [r for r in engine.failure_taxonomy if r['layer'] == 'preflight']
        self.assertEqual(events, [{'layer': 'preflight', 'failure_type': 'preflight_syntax', 'round_index': 0,
                                   'chain_depth': 0, 'was_repaired': True}])

    def test_missing_plan_coverage_is_fixed_in_the_plan_before_the_round_counts(self):
        engine, result, chain = build({**BASE, '.omni/project.json': json.dumps(PLAN_MISSING_A2)}, Repairer())
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0))
        self.assertEqual(json.loads(result.repository['.omni/project.json']), PLAN_OK)
        self.assertEqual(result.repository['app.py'], BASE['app.py'])           # the app was not touched
        self.assertIn('preflight_plan_coverage', [r['failure_type'] for r in engine.failure_taxonomy])


class PreflightNeverHidesARealFailure(unittest.TestCase):
    def test_an_unfixable_syntax_error_still_reaches_the_chain_and_costs_a_real_round(self):
        engine, result, chain = build({**BASE, 'tests/test_app.py': BROKEN_TEST}, Repairer(can_fix=False))
        self.assertEqual(result.status, 'failed')
        self.assertGreaterEqual(result.repair_rounds, 1)
        self.assertEqual(pf.syntax_errors(chain.runs[0]), [{'file': 'tests/test_app.py', 'line': 2,
                                                             'message': 'Python syntax error: unterminated string literal (detected at line 2)'}])
        self.assertFalse([r for r in engine.failure_taxonomy if r['layer'] == 'preflight' and r['was_repaired']])

    def test_a_pre_flight_fix_may_only_touch_the_affected_files(self):
        engine, result, chain = build({**BASE, 'tests/test_app.py': BROKEN_TEST}, Repairer(also_touch_app=True))
        self.assertEqual(chain.runs[0]['app.py'], BASE['app.py'])
        self.assertNotIn('notes.txt', chain.runs[0])


def plan_with(step_change):
    plan = json.loads(json.dumps(PLAN_OK))
    plan['web_saas_acceptance']['personas'][0]['steps'].append(
        {"id": "s3", "kind": "api_smoke", "acceptance_ids": ["A1"], "method": "GET", "path": "/", "expect_status": 200})
    step_change(plan['web_saas_acceptance']['personas'][0]['steps'])
    return plan


class PreflightRunsTheRunnersOwnStepValidation(unittest.TestCase):
    """Paid run 39377332673: "step S5 must reference contract acceptance_ids" cost round 0 although every acceptance
    id was covered by other steps -- the old pre-flight checked coverage only."""

    def test_the_round_0_defect_of_run_39377332673_is_found_statically(self):
        plan = plan_with(lambda steps: steps[2].pop('acceptance_ids'))     # covered A1, A2 elsewhere; s3 has none
        gaps = pf.plan_coverage_gaps({'.omni/project.json': json.dumps(plan)}, SPEC)
        self.assertEqual(gaps, {'invalid': 'step s3 must reference contract acceptance_ids',
                                'missing_acceptance_ids': [], 'missing_kinds': []})

    def test_and_fixed_before_the_round_counts(self):
        plan = plan_with(lambda steps: steps[2].update(acceptance_ids=[]))
        engine, result, chain = build({**BASE, '.omni/project.json': json.dumps(plan)}, Repairer())
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0))
        self.assertEqual(len(chain.runs), 1)
        self.assertEqual(result.repository['app.py'], BASE['app.py'])
        self.assertEqual([(r['failure_type'], r['was_repaired']) for r in engine.failure_taxonomy if r['layer'] == 'preflight'],
                         [('preflight_plan_coverage', True)])

    def test_every_rule_of_the_runner_is_checked(self):
        cases = {
            'step s3 references unknown acceptance id(s): A9': lambda s: s[2].update(acceptance_ids=['A9']),
            'acceptance step ids must be non-empty and unique': lambda s: s[2].update(id='s1'),
            'step s3 requires kind': lambda s: s[2].update(kind=''),
            'step s3 uses unsupported HTTP method TRACE': lambda s: s[2].update(method='TRACE'),
        }
        for message, change in cases.items():
            gaps = pf.plan_coverage_gaps({'.omni/project.json': json.dumps(plan_with(change))}, SPEC)
            self.assertEqual((gaps or {}).get('invalid'), message)
            self.assertIn(f'the plan is invalid: {message}', pf.plan_failure(gaps)['message'])

    def test_a_valid_plan_is_still_clean(self):
        self.assertIsNone(pf.plan_coverage_gaps({'.omni/project.json': json.dumps(plan_with(lambda s: None))}, SPEC))

    def test_an_unfixable_invalid_plan_still_costs_a_real_round(self):
        plan = plan_with(lambda steps: steps[2].pop('acceptance_ids'))
        engine, result, chain = build({**BASE, '.omni/project.json': json.dumps(plan)}, Repairer(can_fix=False))
        self.assertEqual(result.status, 'failed')
        self.assertGreaterEqual(result.repair_rounds, 1)
        self.assertEqual(json.loads(chain.runs[0]['.omni/project.json']), plan)   # reached the chain as it was


@unittest.skipIf(_Chain is None, 'needs the production chain (fastapi)')
class ReviewIsInTheGroup(unittest.TestCase):
    class Gateway:
        accepts_task_tag = False
        last_usage = None

        def complete_json(self, **kw):
            return {'findings': [{'skill': 'skill.form_validation', 'severity': 'blocking', 'file': 'app.py',
                                  'problem': 'invalid score types are accepted', 'fix': 'validate scores'}]}

    def setUp(self):
        self.chain = _Chain()

    def test_review_findings_reach_the_repairer_while_behaviour_also_fails(self):
        # Old: the review wrapped the whole chain and ran only when everything else passed.
        result, repairer, calls = self.chain.build({'behaviour_ok': False}, gateway=self.Gateway())
        self.assertEqual(repairer.received[0][:2], ['BEHAVIOR', 'ALSO_FAILING'])
        self.assertIn('REVIEW: QA review (skill.form_validation)', repairer.messages[0]['ALSO_FAILING'])

    def test_a_review_alongside_other_failures_does_not_use_up_the_review_cap(self):
        result, repairer, calls = self.chain.build({'behaviour_ok': False}, gateway=self.Gateway())
        review = next(e for e in _walk(self.chain.engine.executor) if type(e).__name__ == 'ProductReviewExecutor')
        alongside = [r for r in review.reviews if r['alongside']]
        self.assertTrue(alongside)
        self.assertTrue(all(r['enforced'] for r in alongside))


def _walk(executor):
    seen = 0
    while executor is not None and seen < 25:
        yield executor
        executor = getattr(executor, '__dict__', {}).get('_inner')
        seen += 1


if __name__ == '__main__':
    unittest.main()
