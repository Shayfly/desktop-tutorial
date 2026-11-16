"""Warehouse 104 (released by the owner 2026-11-15): checks that did not run are an explicit list -- in the quality
report, in the build's stored evidence and on the customer's screen -- never a count, never "did not pass or did not run".

Found on a non-founder account's build: the build died in its unit tests, so the trial start-up, the behavioural
acceptance, the browser flow, the layout check and the QA review never ran, and the customer saw one generic sentence.

Real path: release_policy.build_report is the production report; worker_tasks._run_live_build_job runs through the
BuildHarness (the production job, fake engine and platform); app.js's own notRunLine() is executed in node on the
report the production code produced. Nothing here is a hand-written list of checks.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.release_policy import FAIL, NOT_RUN, PASS, build_report
from tests.policy_fixtures import ACCEPTED_SPEC, verified_chain
from tests.test_m3_preview_logic import BuildHarness

APP = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js'
OK = SimpleNamespace(passed=True, score=90, minimum_score=80)
RIGHTS = SimpleNamespace(publish_allowed=True)
# the checks a build that dies in its tests never reaches, in the report's own order
NEVER_REACHED = ['preview_starts', 'behavioural_acceptance', 'browser_flow', 'visual_layout_desktop_mobile', 'qa_review']


def report(evidence, *, passed=True, failures=(), tests_executed=3):
    result = SimpleNamespace(status='ready' if passed else 'failed', spec=ACCEPTED_SPEC,
                             report=ExecutionReport(passed, failures, '', tests_executed=tests_executed))
    return build_report(build_id='b', artifact_sha256='sha', result=result, evidence=evidence, quality=OK,
                        security=OK, rights=RIGHTS, author_models={'author'})


def everything_ran() -> dict:
    return {'consistency_gate': {'last': {'passed': True, 'blocking': [], 'advisories': []}},
            'preview_smoke': {'status': 'PASS'},
            'behavior_acceptance': {'last': {'status': 'PASS', 'summary': 'ok'}},
            'browser_check': {'status': 'passed'},
            'visual_qa': {'status': 'PASS'},
            'product_review': [{'round': 1, 'model': 'reviewer', 'blocking': 0}]}


def died_in_tests():
    """The consistency gate ran; the sandbox tests failed; nothing after them ran."""
    return report({'consistency_gate': {'last': {'passed': True, 'blocking': [], 'advisories': []}}},
                  passed=False, failures=(AcceptanceFailure('A1', 'unit tests failed'),))


def js_not_run_line(build: dict, lang: str) -> str:
    source = APP.read_text(encoding='utf-8')
    translations = source[source.index('const T ='):source.index('const S =')]
    fn = re.search(r'function notRunLine\(.*?\n\}', source, re.S).group()
    js = (translations + f'\nconst S={{lang:{json.dumps(lang)}}};\nfunction t(k){{return T[S.lang][k];}}\n' + fn +
          f'\nconsole.log(JSON.stringify(notRunLine({json.dumps(build, ensure_ascii=False)})));')
    return json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)


class TheReportNamesWhatDidNotRun(unittest.TestCase):
    def test_a_build_that_died_in_its_tests_names_every_check_it_never_reached(self):
        r = died_in_tests()
        self.assertEqual(r.decision, 'FAILED')
        self.assertEqual([c['check'] for c in r.not_run], NEVER_REACHED)
        for entry in r.not_run:
            self.assertEqual(set(entry), {'stage', 'check', 'status', 'required', 'reason'})
            self.assertIn(entry['status'], ('NOT_RUN', 'UNKNOWN', 'NO_CHECKS'))
        required = {c['check'] for c in r.not_run if c['required']}
        self.assertEqual(required, {'preview_starts', 'behavioural_acceptance', 'browser_flow'})   # the advisory two are listed too
        self.assertEqual(r.to_dict()['not_run'], r.not_run)                 # the stored evidence carries the same list

    def test_when_everything_ran_the_list_is_empty(self):
        r = report(everything_ran())
        self.assertEqual(r.decision, 'READY')
        self.assertEqual(r.not_run, [])
        self.assertEqual(r.to_dict()['not_run'], [])

    def test_a_required_check_that_did_not_run_is_listed_and_blocks_ready(self):
        r = report({**everything_ran(), 'preview_smoke': None})
        self.assertEqual([(c['check'], c['required']) for c in r.not_run], [('preview_starts', True)])
        self.assertEqual(r.decision, 'FAILED')
        self.assertIn('preview/preview_starts: NOT_RUN', r.to_dict()['blocking'])

    def test_zero_executed_tests_are_listed_not_passed(self):
        r = report(everything_ran(), tests_executed=0)
        self.assertEqual([c['check'] for c in r.not_run], ['sandbox_build_and_tests'])
        self.assertEqual(r.not_run[0]['status'], 'NO_CHECKS')
        self.assertEqual(r.decision, 'FAILED')


class TheWorkerStoresTheList(unittest.TestCase):
    def test_a_build_whose_browser_check_did_not_run_stores_it_by_name(self):
        h = BuildHarness()
        h.engine.executor = verified_chain(overrides={'browser': {'status': 'unavailable', 'reason': 'no chromium'}})
        self.assertEqual(h.run(), 'failed')
        stored = h.final['evidence_json']['quality_report']['not_run']
        # the harness chain has no visual executor, so the advisory layout check is listed too -- as it should be
        self.assertEqual([(c['check'], c['status']) for c in stored if c['required']], [('browser_flow', NOT_RUN)])
        self.assertEqual([c['check'] for c in stored], ['browser_flow', 'visual_layout_desktop_mobile'])
        self.assertEqual(next(c['reason'] for c in stored if c['check'] == 'browser_flow'), 'no chromium')

    def test_a_ready_build_stores_only_advisory_entries(self):
        h = BuildHarness()
        self.assertEqual(h.run(), 'ready')
        stored = h.final['evidence_json']['quality_report']['not_run']
        self.assertEqual([c['check'] for c in stored], ['visual_layout_desktop_mobile'])   # the fixture chain has no visual QA
        self.assertFalse(any(c['required'] for c in stored))                                # READY never hides a required one

    def test_a_build_that_died_before_the_checks_has_no_report_at_all(self):
        # the UI reads "no report on a failed build" as "no check ran" (notRunLine below)
        h = BuildHarness(engine_exc=RuntimeError('the engine died before any check'))
        with self.assertRaises(RuntimeError):
            h.run()
        self.assertEqual(h.final['error_code'], 'worker_exception')
        self.assertNotIn('quality_report', h.final['evidence_json'])


@unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js notRunLine()')
class TheCustomerReadsTheList(unittest.TestCase):
    def build(self, status, qr):
        return {'status': status, 'error_code': 'verification_failed', 'evidence': {'quality_report': qr}}

    def test_the_failed_build_names_the_five_checks_in_the_customers_words(self):
        qr = died_in_tests().to_dict()
        self.assertEqual(js_not_run_line(self.build('failed', qr), 'he'),
                         'בדיקות שלא רצו: הפעלה ניסיונית, בדיקת התנהגות, בדיקת דפדפן, פריסה במחשב ובטלפון, סקירת איכות.')
        self.assertEqual(js_not_run_line(self.build('failed', qr), 'en'),
                         'Checks that did not run: trial start-up, behaviour check, browser check, layout on desktop and phone, quality review.')

    def test_every_check_the_report_can_name_has_customer_words(self):
        source = APP.read_text(encoding='utf-8')
        names = set(re.findall(r"add\(Check\('[a-z]+', '([a-z_]+)'", Path(APP.parents[1], 'release_policy.py').read_text(encoding='utf-8')))
        self.assertTrue(names)
        blocks = re.findall(r'checkNames:\{([^}]*)\}', source[source.index('const T ='):source.index('const S =')])
        self.assertEqual(len(blocks), 2, 'one checkNames table per language, inside the T literal the UI reads')
        for block in blocks:
            for name in names:
                self.assertIn(f'{name}:', block, name)

    def test_no_report_on_a_failed_build_means_no_check_ran(self):
        self.assertEqual(js_not_run_line({'status': 'failed', 'error_code': 'worker_exception', 'evidence': {}}, 'he'),
                         'אף בדיקה לא רצה: הבנייה נעצרה לפני הבדיקות.')

    def test_a_ready_build_with_everything_run_says_nothing(self):
        self.assertEqual(js_not_run_line(self.build('ready', report(everything_ran()).to_dict()), 'he'), '')

    def test_a_ready_build_with_an_advisory_check_not_run_still_says_so(self):
        r = report({**everything_ran(), 'product_review': []})
        self.assertEqual(r.decision, 'READY')
        self.assertEqual(js_not_run_line(self.build('ready', r.to_dict()), 'he'), 'בדיקות שלא רצו: סקירת איכות.')


if __name__ == '__main__':
    unittest.main()
