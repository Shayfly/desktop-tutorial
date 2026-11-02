"""One verify command per acceptance criterion (founder 2026-11-02 17:22).

bld_2a75e30013d649d3a30fbeb7dcc00b2c: .omni/project.json had ONE verify entry, `python -m pytest -q`, carrying A1..A8.
The round ended "1 failed, 2 passed" and all eight criteria failed -- a partial fix could never look like progress.
Now: the generation constraints ask for one verify entry per acceptance id whose argv names that criterion's pytest node
id, and a pre-flight spec check (round_preflight.verify_granularity_gaps) asks for a narrow fix when that is missing.
The fixtures are the real round-2 manifest and test file of bld_2a75e300 (inspect run 41467881421).
"""
import json
import unittest
from pathlib import Path

from omni_prod import round_preflight as pf
from omni_prod.dependency_policy import GENERATION_CONSTRAINTS
from omni_prod.product_spec import AcceptanceCriterion, ProductSpec, Requirement

FIX = Path(__file__).parent / 'fixtures' / 'verify_per_criterion'
REAL_MANIFEST = (FIX / 'bld_2a75e300_round2_project.json').read_text()
REAL_TESTS = (FIX / 'bld_2a75e300_round2_test_app.py.txt').read_text()
IDS = ['A1', 'A2', 'A3']


def spec(ids=IDS):
    return ProductSpec('scores', 'score keeper', 'web', (Requirement('R1', 'scores'),),
                       tuple(AcceptanceCriterion(a, 'R1', f'criterion {a}') for a in ids))


def manifest(verify, plan=True):
    data = json.loads(REAL_MANIFEST)
    data['verify'] = verify
    if not plan:
        data.pop('web_saas_acceptance', None)       # isolates this check from the behaviour-plan pre-flight
    return json.dumps(data)


def per_criterion(ids=IDS, path='tests/test_app.py'):
    return [{'name': f'{a} check', 'argv': ['python', '-m', 'pytest', '-q', f'{path}::test_{a.lower()}'],
             'acceptance_ids': [a]} for a in ids]


TESTS = ''.join(f'def test_{a.lower()}():\n    assert True\n\n' for a in IDS)


class SpecCheck(unittest.TestCase):
    def test_the_real_bld_2a75e300_manifest_has_no_command_per_criterion(self):
        ids = [f'A{i}' for i in range(1, 9)]
        gaps = pf.verify_granularity_gaps({'.omni/project.json': REAL_MANIFEST, 'tests/test_app.py': REAL_TESTS},
                                          spec(ids))
        print('\n[bld_2a75e300 round 2]', pf.granularity_failure(gaps)['message'][:200])
        self.assertEqual(sorted(gaps['gaps']), ids)
        self.assertTrue(all('no verify entry of its own' in why for why in gaps['gaps'].values()))

    def test_every_id_with_its_own_command_and_an_existing_node_id_passes(self):
        repo = {'.omni/project.json': manifest(per_criterion()), 'tests/test_app.py': TESTS}
        self.assertIsNone(pf.verify_granularity_gaps(repo, spec()))
        params = per_criterion()
        params[0]['argv'][-1] += '[case-1]'                                      # a parametrised node id is fine
        self.assertIsNone(pf.verify_granularity_gaps({'.omni/project.json': manifest(params),
                                                      'tests/test_app.py': TESTS}, spec()))

    def test_each_kind_of_gap_is_named(self):
        shared = per_criterion()[:1] + [{'name': 'rest', 'argv': ['python', '-m', 'pytest', '-q', 'tests/test_app.py::test_a2'],
                                         'acceptance_ids': ['A2', 'A3']}]
        no_node = per_criterion()
        no_node[0]['argv'] = ['python', '-m', 'pytest', '-q', 'tests/test_app.py']
        missing_file = per_criterion(path='tests/test_other.py')
        missing_fn = per_criterion()
        missing_fn[1]['argv'][-1] = 'tests/test_app.py::test_nope'
        cases = {
            'shared': (shared, {'A2': 'no verify entry of its own', 'A3': 'no verify entry of its own'}),
            'no node id': (no_node, {'A1': 'names no pytest node id'}),
            'file missing': (missing_file, {a: 'is not in the repository' for a in IDS}),
            'function missing': (missing_fn, {'A2': 'no test function test_nope'}),
        }
        for name, (verify, expected) in cases.items():
            with self.subTest(name):
                gaps = pf.verify_granularity_gaps({'.omni/project.json': manifest(verify), 'tests/test_app.py': TESTS},
                                                  spec())['gaps']
                self.assertEqual(sorted(gaps), sorted(expected))
                for aid, text in expected.items():
                    self.assertIn(text, gaps[aid])

    def test_nothing_to_check_without_criteria_or_with_a_broken_manifest(self):
        self.assertIsNone(pf.verify_granularity_gaps({'.omni/project.json': REAL_MANIFEST}, spec([])))
        self.assertIsNone(pf.verify_granularity_gaps({'.omni/project.json': '{not json'}, spec()))


class PreflightFixesItWithoutARepairRound(unittest.TestCase):
    def test_a_narrow_fix_is_asked_once_and_adopted_and_the_round_counter_does_not_move(self):
        from omni_prod.autonomous_core import AutonomousProductEngine, ExecutionReport
        from omni_prod.repository_patch import parse_patch
        calls, verified = [], []
        one_command = manifest([{'name': 'unit tests', 'argv': ['python', '-m', 'pytest', '-q'], 'acceptance_ids': IDS}],
                               plan=False)

        class Arch:
            def create_spec(self, prompt):
                return spec()

        class Gen:
            def generate(self, s):
                return parse_patch({'files': [{'path': 'app.py', 'content': 'STATE = 1\n'},
                                              {'path': 'tests/test_app.py', 'content': TESTS},
                                              {'path': '.omni/project.json', 'content': one_command}]})

        class Rep:
            def repair(self, *, spec, repo_summary, failures):
                calls.append([f['acceptance_id'] for f in failures])
                return parse_patch({'files': [{'path': '.omni/project.json', 'content': manifest(per_criterion(), plan=False)},
                                              {'path': 'app.py', 'content': 'STATE = "touched"\n'}]})   # not allowed

        class Ex:
            def execute(self, *, repository, spec):
                verified.append(json.loads(repository['.omni/project.json'])['verify'])
                return ExecutionReport(True)
        e = AutonomousProductEngine(architect=Arch(), generator=Gen(), repairer=Rep(), executor=Ex())
        e._summary = lambda repo, failures=(): {'files': []}
        result = e.build('p')
        events = [x for x in result_events(e) if x['failure_type'] == 'preflight_verify_granularity']
        print('[pre-flight]', calls, events, result.status, result.repair_rounds)
        self.assertEqual(calls, [['VERIFY_GRANULARITY']])
        self.assertEqual(verified, [per_criterion()])                     # round 0 verified the per-criterion manifest
        self.assertEqual(result.repository['app.py'], 'STATE = 1\n')      # the narrow fix touched only allowed files
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0))
        self.assertEqual(events, [{'layer': 'preflight', 'failure_type': 'preflight_verify_granularity',
                                   'round_index': 0, 'chain_depth': 0, 'was_repaired': True}])


def result_events(engine):
    return list(getattr(engine, '_preflight_events', None) or [])


class GenerationConstraints(unittest.TestCase):
    def test_the_constraint_asks_for_one_command_per_criterion_with_a_node_id(self):
        self.assertIn('one "verify" entry for EACH acceptance id', GENERATION_CONSTRAINTS)
        self.assertIn('"tests/test_app.py::test_a1_score_is_saved"], "acceptance_ids": ["A1"]', GENERATION_CONSTRAINTS)


if __name__ == '__main__':
    unittest.main()
