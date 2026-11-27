"""Warehouse 70 (the owner, 2026-11-20: "תעשה את כל מה שיש לנו במחסן"): a failed build tells the customer its real cause.

Production, read-only (build_jobs, failed, 2026-11-17): a build ended as `model_unavailable` with "all model routes
failed: gemini-3.8-flash: model did not return valid JSON". The customer was told "ספקי ה־AI לא היו זמינים כרגע (עומס
או מכסה)" -- the models had answered; none in the required format. Now:
* the routed gateway records what kind of failure each route had (skipped, budget, or the exception's class), and a
  build where every model that was tried answered in a broken format ends as `model_bad_output`, said as such;
  matched by type, never by the message text;
* every code the worker can end a FAILED build with has a customer message in Hebrew and in English, so no customer
  ever reads a bare technical code. A new code without one fails here."""
import json
import re
import subprocess
import unittest
from pathlib import Path

from omni_prod.model_gateway import ModelGatewayError, ModelHTTPError, ModelJSONRejected
from omni_prod.worker_tasks import failure_code
from tests.test_provider_quota_and_dialects import Script, _gw, _model

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'omni_prod' / 'assets' / 'app.js'
WORKER = ROOT / 'omni_prod' / 'worker_tasks.py'
# codes set outside worker_tasks.py on a FAILED build (the reconciler, the queue, the deadline, the image check, the
# requirement split), each named at its source
OTHER_FAILED_CODES = {
    'worker_lost': 'omni_prod/maintenance.py', 'provider_liability_unknown': 'omni_prod/maintenance.py',
    'build_not_found': 'omni_prod/worker_tasks.py BUILD_NOT_FOUND', 'preview_no_build_queue': 'the preview build route',
    'image_mismatch': 'omni_prod/image_match.py', 'needs_customer_input': 'omni_prod/worker_tasks.py',
    'unsupported_dependency': 'the dependency gate',
}
# a cancelled build has its own screen, not an error message
CANCELLED_CODES = {'cancelled_by_user', 'gate_escalation'}


def bad_json(name):
    return ModelJSONRejected(f'model did not return valid JSON (content before the JSON value at char 0 of {name})',
                             raw='Sure! Here is the JSON: {', diagnostic={'reason': 'prose before JSON'})


def worker_failed_codes() -> set:
    src = WORKER.read_text(encoding='utf-8')
    fc = src[src.index('def failure_code'):src.index('def _report_phase')]
    codes = set(re.findall(r"return '([a-z_]+)'", fc))
    codes |= set(re.findall(r"error_code='([a-z_]+)'", src))
    codes |= set(re.findall(r"error_code, error_message = (?:False, )?'([a-z_]+)'", src))
    codes |= set(re.findall(r"return False, '([a-z_]+)'", src))
    codes |= set(re.findall(r"False, '([a-z_]+)',\n", src))
    codes |= set(re.findall(r"getattr\(exc, 'error_code', '([a-z_]+)'\)", src))
    codes |= set(re.findall(r"error_code = '([a-z_]+)'", src))
    return codes - CANCELLED_CODES


def ui_messages(lang: str) -> dict:
    source = APP.read_text(encoding='utf-8')
    translations = source[source.index('const T ='):source.index('const S =')]
    js = translations + f'\nconsole.log(JSON.stringify(T[{json.dumps(lang)}].errCodes));'
    return json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)


class TheRealCause(unittest.TestCase):
    def setUp(self):
        self.models = (_model('primary', 85, '0.75', '3.75'), _model('fallback', 90, '2', '10'))

    def fail(self, plan):
        with self.assertRaises(ModelGatewayError) as ctx:
            _gw(Script(plan), self.models, '1').complete_json(system='s', user='u', max_tokens=1000, task='codegen')
        return ctx.exception

    def test_every_model_answering_in_a_broken_format_is_bad_output_not_load_or_quota(self):
        exc = self.fail({'primary': [bad_json('primary')] * 9, 'fallback': [bad_json('fallback')] * 9})
        self.assertIn('all model routes failed', str(exc))
        self.assertEqual(failure_code(exc), 'model_bad_output')

    def test_a_route_that_did_not_answer_keeps_it_unavailable(self):
        exc = self.fail({'primary': [bad_json('primary')] * 9, 'fallback': [TimeoutError('read timed out')] * 9})
        self.assertEqual(failure_code(exc), 'model_unavailable')
        exc = self.fail({'primary': [ModelHTTPError('HTTP 503: overloaded', status=503)] * 9,
                         'fallback': [ModelHTTPError('HTTP 503: overloaded', status=503)] * 9})
        self.assertEqual(failure_code(exc), 'model_unavailable')

    def test_the_cause_is_read_from_the_failure_types_never_from_the_message_text(self):
        # an error whose text says "valid JSON" but carries no route record is not reclassified
        self.assertEqual(failure_code(ModelGatewayError('all model routes failed: model did not return valid JSON')),
                         'model_unavailable')


class EveryFailureIsExplained(unittest.TestCase):
    maxDiff = None

    def test_every_code_a_failed_build_can_carry_has_a_hebrew_and_an_english_message(self):
        codes = worker_failed_codes() | set(OTHER_FAILED_CODES)
        self.assertIn('model_bad_output', codes)
        for lang in ('he', 'en'):
            with self.subTest(lang):
                missing = sorted(codes - set(ui_messages(lang)))
                self.assertEqual(missing, [], f'{lang}: a failed build would show the customer a bare code')

    def test_every_code_a_failed_build_can_carry_also_has_an_arabic_message(self):
        # warehouse 70: the customer-facing text is in Hebrew, Arabic and English; the first test above covers two
        codes = worker_failed_codes() | set(OTHER_FAILED_CODES)
        missing = sorted(codes - set(ui_messages('ar')))
        self.assertEqual(missing, [], 'ar: a failed build would show the customer a bare code')

    def test_no_failure_message_names_the_platform_or_the_queue(self):
        # warehouse 70: the customer is told what happened to the build, never the machinery (the word "server",
        # the queue, Redis, the worker). Read from the shipped app.js, in all three languages.
        banned = re.compile(r'שרת|server|redis|worker|queue|docker|sandbox|خادم|سيرفر|الخادم', re.IGNORECASE)
        for lang in ('he', 'en', 'ar'):
            for code, text in ui_messages(lang).items():
                with self.subTest(lang=lang, code=code):
                    self.assertIsNone(banned.search(text), f'{lang}/{code} names the machinery: {text}')

    def test_the_bad_output_message_does_not_blame_load_or_quota(self):
        he, en = ui_messages('he')['model_bad_output'], ui_messages('en')['model_bad_output']
        self.assertIn('בפורמט', he)
        self.assertIn('לא בעיה של עומס או מגבלת שימוש', he)
        self.assertIn('not caused by high demand or a usage limit', en)

    def test_a_bad_output_build_is_placed_on_the_generation_step_and_says_no_check_ran(self):
        source = APP.read_text(encoding='utf-8')
        self.assertRegex(source, r"FAIL_STEP = \{[^}]*model_bad_output: 3")
        self.assertRegex(source, r"backendStep\('stepGenerate', 3, \[[^\]]*'model_bad_output'")
        self.assertRegex(source, r"NO_REPORT_BEFORE_CHECKS = \[[^\]]*'model_bad_output'")


if __name__ == '__main__':
    unittest.main()
