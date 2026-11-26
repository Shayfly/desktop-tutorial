"""What the customer is told, and what the stage rows say, come from the version the build KEPT (bld_cb2d1b90, 2026-11-24).

Production (tests/fixtures/repair_converge/bld_cb2d1b90_rounds.json): the kept version was round 0 (4 review findings
and 3 layout failures). The message took the first four items of its report -- the four REVIEW findings -- and dropped
the fifth, the ALSO_FAILING line that carried VISUAL, the real blocker; the announcement skips that line by design, so
the customer never heard of it. The 13 stage rows carried round 0's digest but read the executors' last state, round 6
(a discarded candidate): review PASS ("0 unresolved"), visual FAIL but not required (VISUAL was only in the summary
line), and the sandbox tests FAIL (the summary line's own id was read as a failed test).

Now: the message and the announcement read the kept version's full failure list, lowest stage first, and what does not
fit is counted, never dropped (verification_group.kept_failures / failure_list); the stage rows read the evidence of
the round whose snapshot sha256 is the kept repository's (worker_tasks.RoundEvidence); a check named in ALSO_FAILING
fails and the line itself is not a check (release_policy.kept_failing_ids).

Real path: the worker job (_run_live_build_job through tests/test_m3_preview_logic.BuildHarness) with the REAL engine on
the REAL production chain, answering with production's recorded stage outputs and reviewer findings
(tests/test_repair_converge.production_engine).
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from omni_prod import gate_words
from omni_prod.autonomous_core import AcceptanceFailure as F, ExecutionReport as R
from tests.test_m3_preview_logic import BuildHarness
from tests.test_repair_converge import FIXTURE, production_engine, production_env

BROWSER_DEAD_FORM = ('OMNI_BROWSER_PROBE {"forms": [], "findings": [{"kind": "dead_form", "message": '
                     '"form \'contact\': submitting it sent no request and changed nothing on the page"}]}')


def worker_run(*, max_rounds=6, browser=None):
    calls = []
    with production_env(calls, browser):
        engine, repairer = production_engine(max_rounds=max_rounds)
        h = BuildHarness(verified=False)
        h.engine = engine
        status = h.run()
    ev = h.final['evidence_json']
    rows = {(c['stage'], c['check']): c for c in (ev.get('quality_report') or {}).get('checks', [])}
    return status, h.final, ev, rows


def items(message):
    return message.split('; still failing: ', 1)[1].split('; ')


class TheWorkerReportsTheKeptVersion(unittest.TestCase):
    """The new loop keeps the last adopted round (VISUAL only); the job says exactly that."""

    @classmethod
    def setUpClass(cls):
        cls.status, cls.final, cls.ev, cls.rows = worker_run()

    def test_the_message_names_the_failures_the_kept_version_has(self):
        self.assertEqual(self.status, 'failed')
        listed = items(self.final['error_message'])
        self.assertEqual([i.split(':', 1)[0] for i in listed], ['VISUAL'] * 3)
        self.assertIn('page width 11439px > viewport 1440px', listed[0])

    def test_the_customers_announcement_reads_the_layout_failure(self):
        keys, unworded = gate_words.collect(self.ev['gates']['verification']['failures'])
        self.assertEqual((keys, unworded), (['VISUAL'], []))

    def test_the_stage_rows_read_the_kept_round(self):
        kept = self.ev['kept_round']
        last = self.ev['round_snapshots'][-1]
        self.assertEqual((kept['round'], kept['sha256']), (last['round'], last['sha256']))
        self.assertEqual(self.ev['quality_report']['artifact_sha256'], kept['sha256'])
        self.assertEqual((self.rows[('visual', 'visual_layout_desktop_mobile')]['status'],
                          self.rows[('visual', 'visual_layout_desktop_mobile')]['required']), ('FAIL', True))
        self.assertEqual(self.rows[('tests', 'sandbox_build_and_tests')]['status'], 'PASS')


class RoundZeroKept(unittest.TestCase):
    """No repair round: the kept version is round 0, the version production stored. Production said four review
    findings and nothing else; the job now says all seven failures, the layout ones first."""

    @classmethod
    def setUpClass(cls):
        cls.status, cls.final, cls.ev, cls.rows = worker_run(max_rounds=0)

    def test_every_failure_is_named_lowest_stage_first(self):
        self.assertNotIn('VISUAL', FIXTURE['error_message'])                     # production's message
        listed = items(self.final['error_message'])
        self.assertEqual([i.split(':', 1)[0] for i in listed], ['VISUAL'] * 3 + ['REVIEW'] * 4)
        self.assertLessEqual(len(self.final['error_message']), 2000)
        self.assertEqual([f['acceptance_id'] for f in self.ev['gates']['verification']['failures']],
                         ['VISUAL'] * 3 + ['REVIEW'] * 4)
        self.assertEqual(self.ev['gates']['verification']['reported'][-1]['acceptance_id'], 'ALSO_FAILING')

    def test_the_announcement_says_both_the_layout_and_the_review(self):
        keys, unworded = gate_words.collect(self.ev['gates']['verification']['failures'])
        self.assertEqual((keys, unworded), (['VISUAL', 'REVIEW'], []))
        keys, _ = gate_words.collect(FIXTURE['gates_verification_failures'])     # what production's evidence gave
        self.assertEqual(keys, ['REVIEW'])

    def test_the_rows_are_round_zeros_not_the_last_candidates(self):
        prod = {(r['stage'], r['check']): r for r in FIXTURE['stage_rows']}
        review, visual, tests = (self.rows[('review', 'qa_review_blocking_findings')],
                                 self.rows[('visual', 'visual_layout_desktop_mobile')],
                                 self.rows[('tests', 'sandbox_build_and_tests')])
        self.assertEqual((review['status'], review['detail']),
                         ('FAIL', '4 unresolved blocking finding(s) after 1 review round(s)'))
        self.assertEqual(prod[('review', 'qa_review_blocking_findings')]['status'], 'PASS')        # production: round 6
        self.assertEqual((visual['status'], visual['required']), ('FAIL', True))
        self.assertFalse(prod[('visual', 'visual_layout_desktop_mobile')]['required'])
        self.assertEqual(tests['status'], 'PASS')
        self.assertEqual(prod[('tests', 'sandbox_build_and_tests')]['status'], 'FAIL')


class AKeptVersionThatIsNotTheLastCandidate(unittest.TestCase):
    """Round 1 fixes the review but breaks the browser flow: it is discarded and round 0 is kept. The rows must be
    round 0's (review FAIL, browser PASS), not round 1's (review 0 findings, browser FAIL)."""

    @classmethod
    def setUpClass(cls):
        cls.status, cls.final, cls.ev, cls.rows = worker_run(max_rounds=1, browser={'print("v1")\n': BROWSER_DEAD_FORM})

    def test_round_one_is_discarded_and_round_zero_kept(self):
        self.assertEqual([s['decision'] for s in self.ev['round_snapshots']], ['initial', 'discarded'])
        self.assertEqual(self.ev['kept_round']['round'], 0)
        self.assertEqual(self.ev['kept_round']['sha256'], self.ev['round_snapshots'][0]['sha256'])

    def test_the_rows_are_the_kept_rounds(self):
        self.assertEqual(self.rows[('review', 'qa_review_blocking_findings')]['status'], 'FAIL')
        self.assertEqual(self.rows[('visual', 'browser_flow')]['status'], 'PASS')
        self.assertNotIn('BROWSER', self.final['error_message'])


class ARoundThatDidNotRunAStageHasNoEvidenceForIt(unittest.TestCase):
    """RoundEvidence never lends a round the evidence of an earlier one: a stage whose last result is the same object
    as at the previous capture did not run in this round (the threshold failed before it)."""

    def test_an_unchanged_result_is_not_this_rounds(self):
        from omni_prod.preview_smoke import PreviewReadyExecutor
        from omni_prod.worker_tasks import RoundEvidence
        preview = PreviewReadyExecutor(SimpleNamespace(execute=None))
        engine = SimpleNamespace(executor=preview)
        tracker = RoundEvidence(engine)
        preview.last_smoke = {'status': 'PASS'}
        tracker.capture(0, 'sha-0')
        tracker.capture(1, 'sha-1')                    # round 1 failed before the preview: nothing new
        preview.last_smoke = {'status': 'FAIL'}
        tracker.capture(2, 'sha-2')
        self.assertEqual(tracker.for_version('sha-0')['evidence']['preview_smoke'], {'status': 'PASS'})
        self.assertIsNone(tracker.for_version('sha-1')['evidence']['preview_smoke'])
        self.assertEqual(tracker.for_version('sha-2')['evidence']['preview_smoke'], {'status': 'FAIL'})


class WhatDoesNotFitIsCounted(unittest.TestCase):
    def test_a_long_list_ends_with_the_count_of_what_was_left_out(self):
        from omni_prod.verification_group import failure_list
        failures = [F('VISUAL', 'v' * 200)] * 3 + [F('REVIEW', 'r' * 200)] * 12
        text = failure_list(failures, 1000)
        self.assertLessEqual(len(text), 1000)
        shown = text.count('VISUAL: ') + text.count('REVIEW: ')
        tail = text.rsplit('; ', 1)[1]
        self.assertTrue(tail.startswith(f'(+{15 - shown} more: '), tail)
        self.assertIn('REVIEW', tail)

    def test_a_report_without_the_full_list_keeps_its_summary_line(self):
        """A result with no full list (a modification build's) -- here production's stored round-0 report itself."""
        from omni_prod.worker_tasks import evaluate_release_gates
        stored = tuple(F(g['acceptance_id'], g['message'], g['evidence']) for g in FIXTURE['gates_verification_failures'])
        result = SimpleNamespace(status='failed', report=R(False, stored, ''), repair_rounds=6, stop_reason='')
        ok, code, message = evaluate_release_gates(result=result, quality=None, security=None, rights=None)
        self.assertEqual((ok, code), (False, 'verification_failed'))
        listed = items(message)
        self.assertTrue(listed[0].startswith('ALSO_FAILING: also failing in this round: VISUAL: visual (desktop) '
                                             'h_overflow'), listed[0])                # lowest stage first, never cut
        self.assertEqual([i.split(':', 1)[0] for i in listed[1:]], ['REVIEW'] * 4)


class APolicyReadsTheSummaryLine(unittest.TestCase):
    """Production's stored round-0 report (4 REVIEW + ALSO_FAILING naming VISUAL) through the release policy."""

    def test_a_check_named_in_also_failing_fails_and_the_line_is_not_a_test(self):
        from omni_prod.release_policy import build_report, kept_failing_ids
        stored = tuple(F(g['acceptance_id'], g['message'], g['evidence']) for g in FIXTURE['gates_verification_failures'])
        result = SimpleNamespace(status='failed', report=R(False, stored, '', tests_executed=4),
                                 spec=SimpleNamespace(acceptance=(SimpleNamespace(id='A1'),)), repository={})
        self.assertEqual(kept_failing_ids(result), {'REVIEW', 'VISUAL'})
        ok = SimpleNamespace(passed=True, score=91, minimum_score=80, publish_allowed=True)
        report = build_report(build_id='b', artifact_sha256='s', result=result, evidence={}, quality=ok, security=ok,
                              rights=ok)
        rows = {(c.stage, c.check): c for c in report.checks}
        self.assertEqual((rows[('visual', 'visual_layout_desktop_mobile')].status,
                          rows[('visual', 'visual_layout_desktop_mobile')].required), ('FAIL', True))
        self.assertEqual(rows[('tests', 'sandbox_build_and_tests')].status, 'PASS')


if __name__ == '__main__':
    unittest.main()
