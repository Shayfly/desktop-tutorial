"""78 (Michael 2026-11-11): "the app did not start" is wrong when the app is up. An app that started and served an
empty page is reported as "הממשק שנוצר ריק", with what is missing (form, inputs, button, table)."""
from __future__ import annotations

import pathlib
import subprocess
import unittest
from types import SimpleNamespace

from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.preview_smoke import PREVIEW_FAILURE_ID, PreviewReadyExecutor
from omni_prod.worker_tasks import EMPTY_UI_PREFIX
from omni_prod.worker_tasks import evaluate_release_gates
from tests.test_preview_smoke import APP_TEMPLATE, CRASHING_APP, _LocalSandbox, _repo

ROOT = pathlib.Path(__file__).resolve().parents[1]
# The run-78 page: the app answered, 1744 chars, no form / input / button / table.
STUB = APP_TEMPLATE % ("<!doctype html><html><body><div id='app'>Loading...</div></body></html>", 'text/html')
OK = SimpleNamespace(passed=True, score=90, minimum_score=80, findings=(), blockers=())
RIGHTS = SimpleNamespace(publish_allowed=True, status='CLEAR')


def gate(message, repository=None):
    result = SimpleNamespace(status='failed', repair_rounds=3, repository=repository,
                             report=ExecutionReport(False, (AcceptanceFailure(PREVIEW_FAILURE_ID, message),)))
    return evaluate_release_gates(result=result, quality=OK, security=OK, rights=RIGHTS)


class EndToEnd(unittest.TestCase):
    """The REAL smoke run on a stub app, through the release gate: the words the customer gets."""

    def setUp(self):
        self.ex = PreviewReadyExecutor(_LocalSandbox())

    def test_an_empty_page_is_empty_not_down(self):
        repo = _repo(STUB)
        f = self.ex.execute(repository=repo, spec=None).failures[0]
        _, code, msg = gate(f.message, repo)
        self.assertEqual(code, 'preview_not_ready')
        self.assertTrue(msg.startswith(EMPTY_UI_PREFIX + ' (missing: form,input,button,table)'), msg)

    def test_a_crash_is_still_did_not_start(self):
        repo = _repo(CRASHING_APP)
        f = self.ex.execute(repository=repo, spec=None).failures[0]
        _, code, msg = gate(f.message, repo)
        self.assertIn('did not start for preview', msg)
        self.assertNotIn(EMPTY_UI_PREFIX, msg)

    def test_a_health_string_is_empty_too(self):
        from tests.test_preview_smoke import HEALTH_ONLY_APP
        repo = _repo(HEALTH_ONLY_APP)
        _, _, msg = gate(self.ex.execute(repository=repo, spec=None).failures[0].message, repo)
        self.assertTrue(msg.startswith(EMPTY_UI_PREFIX), msg)

    def test_only_what_is_really_missing_is_named(self):
        repo = {'app.py': "PAGE = '<form><input name=q><button>go</button></form>'"}
        _, _, msg = gate('the app did not start for preview: PREVIEW-SMOKE GET / returned a placeholder page', repo)
        self.assertTrue(msg.startswith(EMPTY_UI_PREFIX + ' (missing: table)'), msg)


class CustomerText(unittest.TestCase):
    """The page's friendlyError, run in node on the real app.js."""

    def say(self, lang, message):
        js = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text()
        start = js.index('const T = {') if 'const T = {' in js else js.index('const T={')
        t_end = js.index('\nconst t = key =>')
        f_start = js.index('function friendlyError(b)')
        f_end = js.index('\n}\n', f_start) + 3
        stubs = ("globalThis.localStorage={getItem(){return null},setItem(){},removeItem(){}};"
                 "globalThis.document={getElementById(){return null},documentElement:{}};"
                 "globalThis.location={search:'',hash:'',pathname:'/'};globalThis.navigator={language:'he'};\n")
        script = (stubs + js[start:t_end] + f'\nS.lang = {lang!r};\n' + js[t_end:js.index('\n', t_end + 1)] + '\n'
                  + js[f_start:f_end] + f'\nconsole.log(friendlyError({{error_code:"preview_not_ready", error_message:{message!r}}}));')
        return subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=30, check=True).stdout.strip()

    def test_hebrew_names_what_is_missing(self):
        out = self.say('he', 'the product passed its checks; the app started but the generated interface is empty: '
                             'PREVIEW-SMOKE GET / returned a placeholder page (missing: form,button,table; 40 chars)')
        self.assertEqual(out, 'הממשק שנוצר ריק: חסרים בו טופס, כפתור, טבלה, ולכן הגרסה לא אושרה.')

    def test_not_started_text_is_unchanged(self):
        out = self.say('he', 'the product passed its checks but did not start for preview after repair: server exited')
        self.assertIn('האתר לא עלה', out)

    def test_english(self):
        out = self.say('en', 'the generated interface is empty (missing: table)')
        self.assertEqual(out, 'The generated interface is empty: missing a table, so the version was not accepted.')


if __name__ == '__main__':
    unittest.main()
