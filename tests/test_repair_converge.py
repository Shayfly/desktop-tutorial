"""The repair loop keeps a repair that works (bld_cb2d1b90a90f430c98603d14f8afa1a8, the owner's build of 2026-11-24).

What production did (tests/fixtures/repair_converge/bld_cb2d1b90_rounds.json, read-only rows): round 0 failed the QA
review (4 findings) AND the layout check (VISUAL, 3 findings). The group put REVIEW at the head because the pointer
pattern read the contrast ratio '3.5:1' as file:line, folded VISUAL into one ALSO_FAILING line, and the loop ranked
the round by its head only: (9, -5). Every repair fixed all four review findings and still failed VISUAL: (7, -3), so
it was called worse and thrown away, six times, and the repairer was told its change made the product worse.

Now (omni_prod/autonomous_core.py judge/rank, omni_prod/verification_group.py _POINTER):
  * a round is ranked by ALL its failures (group_failures), not by the head of its report;
  * a candidate is worse only when it fails a check the best version did not fail AND ranks below it; a strict
    subset of the best version's failures is always adopted;
  * REPAIR_REGRESSION names only the failures the best version did not have;
  * two discarded candidates that fail in exactly the same way stop the loop;
  * a file:line pointer names a file (its extension starts with a letter): '3.5:1' is not one.

Real path: investor_app._verification_executor -- the production chain composition (consistency and dependency gates,
VerificationGroup, preview, behaviour, browser, visual QA, QA review, quality gate) -- through the real
AutonomousProductEngine with production's settings (6 repair rounds, one second chance). Faked: the sandbox transport
(it answers each stage with production's recorded output for that round) and the reviewer model (it answers each
review round with production's recorded findings, in order).
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omni_prod import investor_app
from omni_prod.autonomous_core import (SUMMARY_FAILURE_ID, AcceptanceFailure as F, AutonomousProductEngine,
                                       ExecutionReport as R)
from omni_prod.repository_patch import FilePatch, parse_patch
from tests.test_verification_group import BEHAVIOUR_PASS, BROWSER_OK, Architect, Generator

FIXTURE = json.loads((Path(__file__).resolve().parent / 'fixtures' / 'repair_converge' / 'bld_cb2d1b90_rounds.json')
                     .read_text(encoding='utf-8'))
POINTER_PROBLEM = 'The footer phone is plain text at page.py:88, not a tel: link.'


def visual_output(viewport: str) -> str:
    """The visual QA script's stdout for one viewport, as production recorded the findings (5 controls, 39 texts)."""
    return 'OMNI_VISUAL_QA ' + json.dumps({'viewport': viewport, 'findings': FIXTURE['visual_findings'][viewport],
                                           'controls': 5, 'text_elements': 39}, ensure_ascii=False)


def fake_sandbox(calls: list):
    class FakeRemote:
        def __init__(self, config, **_):
            pass

        def execute(self, *, repository, spec):
            calls.append('threshold')
            return R(True, (), 'unit tests ok', tests_executed=4)

        def _run(self, repository, argv, build_id, profile='default'):
            calls.append(build_id)
            if build_id == 'preview-smoke':
                return {'returncode': 0, 'stdout': '', 'stderr': ''}
            if build_id == 'behavior-acceptance':
                return {'returncode': 0, 'stdout': BEHAVIOUR_PASS, 'stderr': ''}
            if build_id == 'browser-probe':
                return {'returncode': 0, 'stdout': BROWSER_OK, 'stderr': ''}
            if build_id.startswith('visual-'):
                return {'returncode': 0, 'stdout': visual_output(build_id.split('-', 1)[1]), 'stderr': ''}
            return {'returncode': 0, 'stdout': '', 'stderr': ''}
    return FakeRemote


class RecordedReviewer:
    """The reviewer model, answering review round N with production's findings for round N."""

    def __init__(self, reviews):
        self.rounds, self.calls = [r['findings'] for r in reviews], 0
        self.last_usage = SimpleNamespace(model=FIXTURE['reviewer_model'])

    def complete_json(self, **kw):
        self.calls += 1
        return {'findings': [dict(f) for f in self.rounds[min(self.calls, len(self.rounds)) - 1]]}


class Repairer:
    def __init__(self):
        self.received = []

    def repair(self, *, spec, repo_summary, failures):
        self.received.append([dict(f) for f in failures])
        return (FilePatch('app.py', f'print("v{len(self.received)}")\n'),)


ENV = {'OMNI_SANDBOX_RUNNER_URL': 'http://sandbox.invalid', 'OMNI_SANDBOX_SHARED_SECRET': 'x' * 40,
       'OMNI_MIN_QUALITY_SCORE': '0', 'OMNI_MAX_REVIEW_ROUNDS': '2'}


def replay(reviews=None, *, max_rounds: int = 6, retries: int = 1):
    """The production build's rounds on the real chain and loop. Returns (result, engine, repairer, snapshots)."""
    calls, snapshots = [], []
    env = {k: v for k, v in os.environ.items() if k != 'OMNI_VISUAL_QA_ENFORCE'}
    env.update(ENV)
    with mock.patch.dict(os.environ, env, clear=True), \
            mock.patch.object(investor_app, 'RemoteSandboxRepositoryExecutor', fake_sandbox(calls)):
        executor = investor_app._verification_executor(RecordedReviewer(reviews or FIXTURE['reviews']))
        repairer = Repairer()
        engine = AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=repairer,
                                         executor=executor, max_repair_rounds=max_rounds, repair_ceiling=6)
        engine.no_progress_retries = retries                    # production: OMNI_NO_PROGRESS_RETRIES=1
        engine.round_hook = lambda i, repo, report, decision, progress: snapshots.append(
            {'round': i, 'decision': decision, 'progress': list(progress),
             'failing': sorted({f.acceptance_id for f in report.failures})})
        result = engine.build('the owner\'s brief')
    return result, engine, repairer, snapshots


def with_pointer(reviews):
    """Production's reviews, with the tel: finding carrying a real file:line pointer (a review finding that names a
    line is the head of the round even with the corrected pattern)."""
    out = json.loads(json.dumps(reviews))
    out[0]['findings'][3]['problem'] = POINTER_PROBLEM
    return out


VISUAL_MESSAGES = ['visual (desktop) h_overflow:  page width 11439px > viewport 1440px',
                   'visual (mobile) no_mobile_viewport:  layout width 1560px on a 390px phone (no meta viewport): '
                   'the page is shown zoomed out',
                   'visual (mobile) h_overflow:  page width 10389px > viewport 1560px']


class TheProductionRoundsOnTheRealChain(unittest.TestCase):
    """The six rounds production threw away are adopted; the loop stops on the repeated failure, not the round cap."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.engine, cls.repairer, cls.snapshots = replay()

    def test_the_fixture_is_production_verbatim(self):
        import hashlib
        md5 = lambda s: hashlib.md5(s.encode('utf-8')).hexdigest()
        db = FIXTURE['md5_from_the_database']
        self.assertEqual([md5(g['message']) for g in FIXTURE['gates_verification_failures']],
                         db['gates_verification_failures.message'])
        self.assertEqual(md5(FIXTURE['error_message']), db['error_message'])
        self.assertEqual([md5(f['problem']) for f in FIXTURE['reviews'][0]['findings']], db['review_round_1_problem'])
        self.assertEqual(md5(FIXTURE['visual_findings']['desktop'][0]['detail']), db['visual_detail']['desktop h_overflow'])

    def test_round_zero_fails_review_and_visual_and_is_ranked_by_both(self):
        first = self.snapshots[0]
        self.assertEqual(first['decision'], 'initial')
        self.assertEqual(first['progress'], [7, -7])                 # VISUAL is its lowest stage; 4 + 3 failures
        full = self.engine.round_failures[0]
        self.assertEqual(sorted({f.acceptance_id for f in full}), ['REVIEW', 'VISUAL'])
        self.assertEqual([f.message for f in full if f.acceptance_id == 'VISUAL'], VISUAL_MESSAGES)

    def test_the_repair_that_fixed_the_review_is_adopted_not_discarded(self):
        self.assertEqual(self.snapshots[1]['failing'], ['VISUAL'])
        self.assertEqual(self.snapshots[1]['decision'], 'adopted')
        self.assertEqual(self.snapshots[1]['progress'], [7, -3])
        self.assertNotIn('discarded', [s['decision'] for s in self.snapshots])

    def test_no_repairer_is_told_its_change_made_the_product_worse(self):
        told = [f['acceptance_id'] for call in self.repairer.received for f in call]
        self.assertNotIn('REPAIR_REGRESSION', told)

    def test_the_loop_stops_on_the_repeated_failure_and_keeps_the_version_without_review_findings(self):
        self.assertEqual(self.result.status, 'failed')
        self.assertEqual(self.result.stop_reason, 'no_progress_same_failure')
        self.assertEqual(self.result.repair_rounds, 3)                # not six paid rounds
        self.assertEqual([s['decision'] for s in self.snapshots], ['initial', 'adopted', 'adopted', 'adopted'])
        self.assertEqual([f.message for f in self.result.full_failures], VISUAL_MESSAGES)

    def test_after_round_one_the_repairer_is_handed_the_layout_failure_in_full(self):
        second = self.repairer.received[1]
        self.assertEqual([f['acceptance_id'] for f in second], ['VISUAL'] * 3)
        self.assertIn('page width 11439px > viewport 1440px', second[0]['message'])


class AReviewFindingWithARealPointer(unittest.TestCase):
    """Production's rounds with one review finding naming page.py:88: REVIEW is the head of round 0 (the pointer wins
    within ranks 4-9), so a loop that ranks by the head alone discards the round-1 repair again."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.engine, cls.repairer, cls.snapshots = replay(with_pointer(FIXTURE['reviews']))

    def test_review_is_the_head_of_round_zero(self):
        self.assertEqual(self.snapshots[0]['failing'], [SUMMARY_FAILURE_ID, 'REVIEW'])
        self.assertEqual([f['acceptance_id'] for f in self.repairer.received[0]], ['REVIEW'] * 4 + [SUMMARY_FAILURE_ID])

    def test_the_review_fixing_repair_is_still_adopted(self):
        self.assertEqual(self.snapshots[0]['progress'], [7, -7])
        self.assertEqual(self.snapshots[1]['decision'], 'adopted')
        self.assertNotIn('discarded', [s['decision'] for s in self.snapshots])
        self.assertEqual(self.result.stop_reason, 'no_progress_same_failure')
        self.assertEqual([f.message for f in self.result.full_failures], VISUAL_MESSAGES)


class APointerNamesAFile(unittest.TestCase):
    def test_a_contrast_ratio_is_not_a_pointer(self):
        from omni_prod.verification_group import _POINTER
        for text in FIXTURE['gates_verification_failures'][1]['message'], 'ratio 4.5:1', 'a 10.0:1 ratio':
            self.assertIsNone(_POINTER.search(text), text)
        for text in ('at app.py:23', 'static/app.js:41', 'templates/v1.2.html:7'):
            self.assertIsNotNone(_POINTER.search(text), text)

    def test_round_zero_of_production_puts_the_layout_failure_at_the_head(self):
        result, engine, repairer, snapshots = replay(max_rounds=1)
        self.assertEqual(snapshots[0]['failing'], [SUMMARY_FAILURE_ID, 'VISUAL'])
        first = repairer.received[0]
        self.assertEqual([f['acceptance_id'] for f in first], ['VISUAL'] * 3 + [SUMMARY_FAILURE_ID])
        self.assertTrue(first[-1]['message'].startswith('also failing in this round: REVIEW: QA review (spec): GET '
                                                        '/health'), first[-1]['message'])


# ---------------------------------------------------------------- the decision, on small reports --------------------
class _Seq:
    """Executor answering each repository version with a fixed report (app.py holds the version)."""

    def __init__(self, reports, group=None):
        self.reports, self.group, self.runs = reports, group or {}, []
        self.group_failures = ()

    def execute(self, *, repository, spec):
        v = repository['app.py']
        self.runs.append(v)
        self.group_failures = self.group.get(v, ())
        return self.reports[v]


class _Rep:
    def __init__(self):
        self.calls = []

    def repair(self, **kw):
        self.calls.append(kw['failures'])
        return parse_patch({'files': [{'path': 'app.py', 'content': f'v{len(self.calls)}'}]})


class _Gen:
    def generate(self, spec):
        return parse_patch({'files': [{'path': 'app.py', 'content': 'v0'}]})


def _run(reports, group=None, rounds=4):
    rep, ex = _Rep(), _Seq(reports, group)
    engine = AutonomousProductEngine(architect=SimpleNamespace(create_spec=lambda p: 'spec'), generator=_Gen(),
                                     repairer=rep, executor=ex, max_repair_rounds=rounds)
    decisions = []
    engine.round_hook = lambda i, repo, report, decision, progress: decisions.append(decision)
    return engine.build('p'), rep, ex, decisions


VIS = F('VISUAL', 'visual (desktop) h_overflow:  page width 11439px > viewport 1440px')
BROWSER = F('BROWSER', 'the product misbehaves in a real browser: dead form')


class TheDecision(unittest.TestCase):
    def test_a_strict_subset_of_the_best_failures_is_adopted(self):
        best = [F('REVIEW', 'r1'), F('REVIEW', 'r2'), VIS]
        self.assertEqual(AutonomousProductEngine.judge([VIS], best), (False, True))

    def test_a_new_failure_at_an_earlier_stage_is_worse(self):
        self.assertEqual(AutonomousProductEngine.judge([VIS, BROWSER], [VIS]), (True, False))

    def test_the_same_criterion_failing_at_an_earlier_stage_is_a_new_check(self):
        # A1's acceptance test failed in the best version; a candidate whose A1 does not even build is worse
        best = [F('A1', 'remote verification failed: acceptance tests: 1 failed')]
        cand = [F('A1', 'remote build failed: at app.py:3')]
        self.assertEqual(AutonomousProductEngine.judge(cand, best), (True, False))

    def test_more_failures_of_the_same_checks_are_adopted_but_do_not_become_the_best(self):
        best = [VIS]
        cand = [VIS, F('VISUAL', 'visual (mobile) h_overflow:  page width 10389px > viewport 1560px')]
        self.assertEqual(AutonomousProductEngine.judge(cand, best), (False, False))

    def test_regression_note_names_only_what_the_candidate_broke(self):
        reports = {'v0': R(False, (VIS,)), 'v1': R(False, (BROWSER, F(SUMMARY_FAILURE_ID, 'also failing: VISUAL'))),
                   'v2': R(True)}
        group = {'v1': (BROWSER, VIS)}
        result, rep, ex, decisions = _run(reports, group)
        self.assertEqual(decisions, ['initial', 'discarded', 'passed'])
        note = next(f for f in rep.calls[1] if f['acceptance_id'] == 'REPAIR_REGRESSION')
        self.assertIn('BROWSER', note['evidence'])
        self.assertNotIn('11439px', note['evidence'])                   # VISUAL failed before the repair too

    def test_two_discarded_candidates_that_fail_alike_stop_the_loop(self):
        reports = {'v0': R(False, (VIS,)), 'v1': R(False, (VIS, BROWSER)), 'v2': R(False, (VIS, BROWSER)),
                   'v3': R(True)}
        result, rep, ex, decisions = _run(reports)
        self.assertEqual(decisions, ['initial', 'discarded', 'discarded'])
        self.assertEqual((result.stop_reason, result.repair_rounds), ('no_progress_same_failure', 2))
        self.assertEqual(ex.runs, ['v0', 'v1', 'v2'])                  # v3 is never paid for
        self.assertEqual(result.repository['app.py'], 'v0')            # the best version is kept

    def test_the_result_carries_the_kept_versions_full_failure_list(self):
        reports = {'v0': R(False, (F('REVIEW', 'r1'), F(SUMMARY_FAILURE_ID, 'also failing: VISUAL')))}
        group = {'v0': (F('REVIEW', 'r1'), VIS)}
        result, rep, ex, decisions = _run(reports, group, rounds=0)
        self.assertEqual([f.acceptance_id for f in result.full_failures], ['REVIEW', 'VISUAL'])


if __name__ == '__main__':
    unittest.main()
