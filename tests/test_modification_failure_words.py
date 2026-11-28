"""Warehouse 70 (the owner, 2026-11-20): a failed change request tells the customer what really happened.

Root cause, read from the code: a build that fails has words by code (app.js errCodes, via friendlyError/failureView).
A change request (modification_requests) that fails did not use them: renderMod printed `error_message` raw -- the
engine's English ("quality score 61 below minimum 70 (...)", "ModelGatewayError: all model routes failed: gemini-...") --
and its code is the engine's gate name (worker_tasks.execute_modification_job: error_code = blocking_gate), one of
verification / quality / security / rights, which errCodes does not know. A queue failure of a change (worker_lost,
provider_liability_unknown, build_timeout, model_unavailable ...) was printed the same way.

On the real path: app.js is executed as shipped (its tables and functions, in node); the gate names are read from
modification_engine.py itself; failure_code is called with real exception types.
"""
import json
import logging
import re
import subprocess
import unittest
from pathlib import Path

from omni_prod.worker_tasks import failure_code
from tests.test_error_codes_tell_the_real_cause import OTHER_FAILED_CODES, ui_messages, worker_failed_codes

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'omni_prod' / 'assets' / 'app.js'
ENGINE = ROOT / 'omni_prod' / 'modification_engine.py'
RAW = 'ModelGatewayError: all model routes failed: gemini-3.8-flash: model did not return valid JSON; quality score 61'
LANGS = ('he', 'en', 'ar')


def _fn(source, name):
    found = re.search(r'^(?:async )?function ' + name + r'\(.*?\n\}', source, re.S | re.M)
    assert found, f'app.js has no function {name}'
    return found.group()


def _const(source, name):
    found = re.search(r'^const ' + name + r' = .*;$', source, re.M)
    assert found, f'app.js has no const {name}'
    return found.group()


def run_js(expression, *, lang='he', me=None):
    """(value, console.error lines) of `expression` against app.js's own tables and functions."""
    source = APP.read_text(encoding='utf-8')
    tables = source[source.index('const T ='):source.index('const S =')]
    assigns = '\n'.join(re.findall(r'^Object\.assign\(T\.(?:he|en), \{.*?\}\);$', source, re.S | re.M))
    parts = [tables, f'const S = {{lang: {json.dumps(lang)}, me: {json.dumps(me)}, signedIn: true}};', assigns,
             'function t(k) { return T[S.lang][k]; }',
             'const __errors = []; console.error = (m) => __errors.push(String(m));',
             *(_const(source, c) for c in ('NOT_CHARGED_BILLING', 'NOT_CHARGED_CODES', 'CHARGE_UNKNOWN_CODES', 'FAIL_ACTION',
                                           'MOD_GATE_CODES')),
             *(_fn(source, f) for f in ('notRunLine', 'stopReasonLine', 'friendlyError', 'ownerView', 'failureView',
                                        'modFailureView', 'requestEditLabel')),
             f'console.log(JSON.stringify([{expression}, __errors]));']
    done = subprocess.run(['node', '-'], input='\n'.join(parts), capture_output=True, text=True, timeout=50)
    assert done.returncode == 0, done.stderr[-1500:]
    return json.loads(done.stdout)


def failed_mod(code, **evidence):
    return {'status': 'FAILED', 'error_code': code, 'error_message': RAW, 'evidence': evidence}


def engine_gate_names():
    return set(re.findall(r"GateResult\(False, '([a-z_]+)'", ENGINE.read_text(encoding='utf-8')))


class AFailedChangeIsSaidInTheCustomersWords(unittest.TestCase):
    def test_the_gate_names_the_engine_can_fail_a_change_with_are_all_mapped_to_words(self):
        gates = engine_gate_names()
        self.assertEqual(gates, {'verification', 'quality', 'security', 'rights'})
        mapped, _ = run_js('MOD_GATE_CODES')
        self.assertEqual(set(mapped), gates)
        for lang in LANGS:
            words = set(ui_messages(lang))
            for gate, code in mapped.items():
                with self.subTest(lang=lang, gate=gate):
                    self.assertIn(code, words)

    def test_every_gate_and_every_queue_failure_of_a_change_reads_its_own_words_never_the_raw_text(self):
        gates = sorted(engine_gate_names())
        queue = sorted((worker_failed_codes() | set(OTHER_FAILED_CODES)) - {'preview_no_build_queue'})
        mapped, _ = run_js('MOD_GATE_CODES')
        for lang in LANGS:
            known = ui_messages(lang)
            for code in gates + queue:
                with self.subTest(lang=lang, code=code):
                    view, errors = run_js(f'modFailureView({json.dumps(failed_mod(code))})', lang=lang)
                    self.assertEqual(errors, [], f'{code} has no words')
                    for leak in ('ModelGatewayError', 'gemini', 'quality score', 'routes failed', 'valid JSON', code):
                        self.assertNotIn(leak, view['text'])
                    self.assertTrue(view['text'].rstrip().endswith('".'), view['text'])
                    # the sentence is the code's own (a gate name through its mapping), not the default line
                    self.assertIn(known[mapped.get(code, code)], view['text'])

    def test_a_failed_change_names_the_button_it_has_not_the_builds(self):
        view, _ = run_js(f'modFailureView({json.dumps(failed_mod("worker_lost"))})')
        self.assertTrue(view['text'].endswith('לחצו על "שליחת שינוי".'), view['text'])
        self.assertNotIn('לנסות לבנות שוב', view['text'])
        view, _ = run_js(f'modFailureView({json.dumps(failed_mod("worker_lost"))})', lang='en')
        self.assertTrue(view['text'].endswith('press "Send change".'), view['text'])

    def test_not_charged_is_said_only_when_the_record_says_so(self):
        released, _ = run_js(f'modFailureView({json.dumps(failed_mod("worker_lost", billing="released"))})')
        self.assertIn('הבנייה נתקעה ועצרנו אותה.', released['text'])
        self.assertIn('לא חויבתם.', released['text'])
        unknown, _ = run_js(
            f'modFailureView({json.dumps(failed_mod("provider_liability_unknown", billing="released"))})')
        self.assertNotIn('לא חויבתם.', unknown['text'])
        self.assertIn('עוד לא ידוע אם חויבתם', unknown['text'])

    def test_an_unknown_code_fails_loudly_and_still_never_shows_the_raw_text(self):
        for code in ('a_code_nobody_wrote_words_for', None, 'quality '):
            with self.subTest(code=code):
                view, errors = run_js(f'modFailureView({json.dumps(failed_mod(code))})')
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('no customer words for failure code', errors[0])
                self.assertIn('הבנייה לא הצליחה בגלל תקלה אצלנו.', view['text'])
                self.assertNotIn('ModelGatewayError', view['text'])

    def test_a_failed_build_with_an_unknown_code_is_loud_too(self):
        text, errors = run_js(
            'friendlyError({status: "failed", error_code: "a_code_nobody_wrote_words_for", error_message: "x"})')
        self.assertIn('הבנייה לא הצליחה בגלל תקלה אצלנו.', text)
        self.assertEqual(len(errors), 1)
        _, errors = run_js('friendlyError({status: "failed", error_code: "worker_lost", error_message: "x"})')
        self.assertEqual(errors, [])

    def test_renderMod_uses_it_for_failed_changes_and_only_the_owner_sees_the_raw_text(self):
        source = APP.read_text(encoding='utf-8')
        body = source[source.index('function renderMod'):]
        body = body[:body.index('box.replaceChildren(...kids)')]
        self.assertRegex(body, r"m\.status === 'FAILED'\) \{\s*const mv = modFailureView\(m\)")
        self.assertRegex(body, r"ownerView\(\) && mv\.raw")
        self.assertNotRegex(body, r"\['FAILED', 'ERROR'")        # FAILED is not in the raw-text list any more


class TheCatchAllIsNotSilent(unittest.TestCase):
    def test_an_exception_with_no_code_of_its_own_is_named_in_the_log(self):
        class SomethingNew(Exception):
            pass
        with self.assertLogs('omni_prod.worker_tasks', level=logging.ERROR) as cm:
            self.assertEqual(failure_code(SomethingNew('x')), 'worker_exception')
        self.assertIn('SomethingNew', cm.output[0])

    def test_an_exception_with_a_code_of_its_own_logs_nothing(self):
        from omni_prod.build_control import BuildDeadline
        with self.assertNoLogs('omni_prod.worker_tasks', level=logging.ERROR):
            self.assertEqual(failure_code(BuildDeadline('late')), 'build_timeout')


if __name__ == '__main__':
    unittest.main()
