"""The round-0 behavioural plan is a floor for repair rounds (founder 2026-11-02 01:18, direction b).

bld_96ab03c8 and bld_99ea49df: in round 1 the repairer returned .omni/project.json without web_saas_acceptance
(1063 B -> 341 B) and it stayed that way. Now: the round-0 block is put back, the rest of the round's changes are
kept, the acceptance check runs against the ORIGINAL block, and the next repair is told (REPAIR_PLAN_WEAKENED).
The fixtures are the real round-0 / round-1 manifests of bld_99ea49dfc6c843aabc90bb8cccbcc1d7 (inspect run 41359323967).
"""
import json
import unittest
from pathlib import Path

from omni_prod import plan_floor
from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.repository_patch import parse_patch

FIX = Path(__file__).parent / 'fixtures' / 'plan_floor'
ROUND0 = (FIX / 'bld_99ea49df_round0_project.json').read_text()
ROUND1 = (FIX / 'bld_99ea49df_round1_project.json').read_text()
FLOOR = json.loads(ROUND0)['web_saas_acceptance']
S2 = next(s for s in FLOOR['personas'][0]['steps'] if s['id'] == 'S2')       # POST score 2.9 -> 400


def py(state):
    return f'STATE = {state!r}\n'           # valid Python, so the round pre-flight (syntax) has nothing to do


def manifest_with(block=None, **changes):
    data = json.loads(ROUND1)
    data.update(changes)
    if block is not None:
        data['web_saas_acceptance'] = block
    return json.dumps(data)


class TheRealBuild(unittest.TestCase):
    def test_bld_99ea49df_round1_is_detected_and_restored_keeping_the_rest(self):
        candidate = {'app.py': 'fixed app', 'tests/test_app.py': 'new tests', '.omni/project.json': ROUND1}
        restored, lost = plan_floor.enforce(candidate, FLOOR)
        print('\n[bld_99ea49df r0->r1]', lost)
        self.assertEqual(lost, ['the whole web_saas_acceptance block'])
        self.assertEqual(plan_floor.plan_block(restored), FLOOR)
        self.assertEqual((restored['app.py'], restored['tests/test_app.py']), ('fixed app', 'new tests'))
        self.assertEqual(json.loads(restored['.omni/project.json'])['verify'], json.loads(ROUND1)['verify'])


class WhatCountsAsWeakening(unittest.TestCase):
    def test_removed_or_changed_step_and_dropped_kind(self):
        steps = [s for s in FLOOR['personas'][0]['steps'] if s['id'] != 'S2']
        cut = dict(FLOOR, personas=[dict(FLOOR['personas'][0], steps=steps)])
        self.assertEqual(plan_floor.weakened(FLOOR, cut), ['step S2 (POST /api/scores -> 400)'])
        changed = json.loads(json.dumps(FLOOR))
        changed['personas'][0]['steps'][1]['expect_status'] = 201                # 2.9 now "accepted"
        self.assertEqual(plan_floor.weakened(FLOOR, changed), ['step S2 (POST /api/scores -> 400)'])
        fewer_kinds = dict(FLOOR, required_kinds=['data_read'])
        self.assertEqual(plan_floor.weakened(FLOOR, fewer_kinds),
                         ['required kind data_create', 'required kind responsive', 'required kind api_smoke'])

    def test_additions_and_no_round0_plan_are_not_weakening(self):
        more = json.loads(json.dumps(FLOOR))
        more['personas'][0]['steps'].append({'id': 'S9', 'kind': 'data_read', 'acceptance_ids': ['A1'],
                                             'method': 'GET', 'path': '/healthz', 'expect_status': 200})
        more['required_kinds'].append('extra')
        self.assertEqual(plan_floor.weakened(FLOOR, more), [])
        self.assertEqual(plan_floor.enforce({'.omni/project.json': ROUND1}, None), ({'.omni/project.json': ROUND1}, []))


class BuildLoop(unittest.TestCase):
    """The engine with a fake repairer and an executor that plays the behaviour check: it passes only when the app
    is fixed AND the plan it is given still has step S2 -- i.e. when it is checked against the original plan."""

    def engine(self, repairs, rounds=3):
        seen_plans, repair_inputs = [], []

        class Arch:
            def create_spec(self, prompt):
                return 'spec'

        class Gen:
            def generate(self, spec):
                return parse_patch({'files': [{'path': 'app.py', 'content': py('broken')},
                                              {'path': '.omni/project.json', 'content': ROUND0}]})

        class Rep:
            def repair(self, *, spec, repo_summary, failures):
                repair_inputs.append([f['acceptance_id'] for f in failures])
                return parse_patch({'files': repairs[len(repair_inputs) - 1]})

        class Ex:
            def execute(self, *, repository, spec):
                block = plan_floor.plan_block(repository)
                seen_plans.append(block)
                if block is None:
                    return ExecutionReport(False, (AcceptanceFailure('BEHAVIOR', 'the product has no behavioural acceptance plan'),))
                has_s2 = S2 in [s for p in block['personas'] for s in p['steps']]
                if 'fixed' in repository['app.py'] and has_s2:
                    return ExecutionReport(True)
                return ExecutionReport(False, (AcceptanceFailure('A3', f"S2 2.9 accepted at {repository['app.py']}"),))
        e = AutonomousProductEngine(architect=Arch(), generator=Gen(), repairer=Rep(), executor=Ex(),
                                    max_repair_rounds=rounds)
        e._summary = lambda repo, failures=(): {'files': []}
        return e, seen_plans, repair_inputs

    def test_a_round_that_cuts_the_block_and_passes_is_checked_against_the_original(self):
        e, plans, _ = self.engine([[{'path': 'app.py', 'content': py('fixed app')},
                                    {'path': '.omni/project.json', 'content': ROUND1}]])
        result = e.build('p')
        print('\n[cut + fix]', result.status, result.stop_reason, e.trace[0].get('plan_restored'))
        self.assertEqual((result.status, result.stop_reason, result.repair_rounds), ('ready', 'passed', 1))
        self.assertEqual(plans[-1], FLOOR)                          # acceptance ran against the ORIGINAL block
        self.assertEqual(plan_floor.plan_block(result.repository), FLOOR)
        self.assertEqual(result.repository['app.py'], py('fixed app'))  # the round's code change is kept
        self.assertEqual(e.trace[0]['plan_restored'], ['the whole web_saas_acceptance block'])

    def test_cutting_only_s2_does_not_make_a_broken_app_pass_and_the_next_repair_is_told(self):
        steps = [s for s in FLOOR['personas'][0]['steps'] if s['id'] != 'S2']
        cut = manifest_with(dict(FLOOR, personas=[dict(FLOOR['personas'][0], steps=steps)]))
        e, plans, inputs = self.engine([[{'path': 'app.py', 'content': py('still broken 1')},
                                         {'path': '.omni/project.json', 'content': cut}],
                                        [{'path': 'app.py', 'content': py('fixed app')}]])
        result = e.build('p')
        print('[cut S2]', result.status, inputs)
        self.assertTrue(all(p == FLOOR for p in plans))            # every round was checked against the floor
        self.assertIn(plan_floor.PLAN_WEAKENED_ID, inputs[1])      # repair 2 hears about it
        self.assertNotIn(plan_floor.PLAN_WEAKENED_ID, inputs[0])
        self.assertEqual((result.status, result.repair_rounds), ('ready', 2))

    def test_a_repair_that_only_cut_the_plan_is_unchanged_not_a_new_paid_check(self):
        e, plans, _ = self.engine([[{'path': '.omni/project.json', 'content': ROUND1}]])
        result = e.build('p')
        self.assertEqual((result.stop_reason, len(plans)), ('no_progress_repository_unchanged', 1))



class FreeRepairLoop(unittest.TestCase):
    """modifier_engine.run_free_repair (founder 2026-11-02 16:48): the floor is the plan of the repository the
    modification starts from."""

    def run_loop(self, repairs, rounds=3):
        from omni_prod.change_policy import ChangeAssessment
        from omni_prod.modifier_engine import run_free_repair
        plans, inputs = [], []

        class Rep:
            def repair(self, *, spec, repo_summary, failures):
                inputs.append([f['acceptance_id'] for f in failures])
                return parse_patch({'files': repairs[len(inputs) - 1]})

        class Ex:
            def execute(self, *, repository, spec):
                block = plan_floor.plan_block(repository)
                plans.append(block)
                has_s2 = bool(block) and S2 in [s for p in block['personas'] for s in p['steps']]
                if 'fixed' in repository['app.py'] and has_s2:
                    return ExecutionReport(True)
                return ExecutionReport(False, (AcceptanceFailure('A3', f"S2 2.9 accepted at {repository['app.py']}"),))
        start = {'app.py': py('broken'), '.omni/project.json': ROUND0}
        out = run_free_repair(spec=None, repository=start,
                              assessment=ChangeAssessment('system_bug', '2.9 is accepted', ('A3',), False),
                              followup='a score of 2.9 is accepted', repairer=Rep(), executor=Ex(),
                              max_repair_rounds=rounds)
        return out, plans, inputs

    def test_a_round_that_cuts_the_block_and_passes_is_checked_against_the_original(self):
        (repo, rounds, report), plans, _ = self.run_loop([[{'path': 'app.py', 'content': py('fixed app')},
                                                           {'path': '.omni/project.json', 'content': ROUND1}]])
        print('\n[free repair, cut + fix]', rounds, report.passed)
        self.assertTrue(report.passed)
        self.assertEqual(plans, [FLOOR])                            # verified against the ORIGINAL block
        self.assertEqual(plan_floor.plan_block(repo), FLOOR)
        self.assertEqual(repo['app.py'], py('fixed app'))           # the round's code change is kept

    def test_a_cut_round_that_still_fails_tells_the_next_repair(self):
        (repo, rounds, report), plans, inputs = self.run_loop(
            [[{'path': 'app.py', 'content': py('still broken')}, {'path': '.omni/project.json', 'content': ROUND1}],
             [{'path': 'app.py', 'content': py('fixed app')}]])
        print('[free repair, cut S2 then fix]', inputs)
        self.assertEqual(inputs[1], ['A3', plan_floor.PLAN_WEAKENED_ID])
        self.assertTrue(all(p == FLOOR for p in plans))
        self.assertTrue(report.passed)

    def test_no_plan_at_the_start_means_no_floor(self):
        from omni_prod.change_policy import ChangeAssessment
        from omni_prod.modifier_engine import run_free_repair

        class Rep:
            def repair(self, **kw):
                return parse_patch({'files': [{'path': 'app.py', 'content': py('fixed')}]})

        class Ex:
            def execute(self, *, repository, spec):
                return ExecutionReport(True)
        repo, rounds, report = run_free_repair(spec=None, repository={'app.py': py('x'), '.omni/project.json': ROUND1},
                                               assessment=ChangeAssessment('system_bug', 'r', ('A1',), False),
                                               followup='f', repairer=Rep(), executor=Ex())
        self.assertEqual(repo['.omni/project.json'], ROUND1)

if __name__ == '__main__':
    unittest.main()
