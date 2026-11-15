"""Warehouse 102, narrow scope (owner 2026-11-15): when the automatic repair stops because the repository did not change,
the loop stops at once (it does, since 2026-10-07: tests/test_repair_stop_loss.py) and the reason reaches the customer's
screen -- not only the job's evidence.

Found on a non-founder account's build (bld_7fb5e1b2 and others): the engine stopped with
`no_progress_repository_unchanged`, the worker stored it as evidence.repair_stop_reason, and the customer read only
"the build failed" with the repair-round count.

Real path: the real AutonomousProductEngine loop (fake repairer and sandbox, as in test_repair_stop_loss), the real
worker job through the BuildHarness, the real customer view filter, and app.js's own stopReasonLine() executed in node.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from omni_prod.customer_views import strip_internal_economics
from tests.test_m3_preview_logic import BuildHarness
from tests.test_repair_stop_loss import _engine, _Executor, _Repairer

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'omni_prod' / 'assets' / 'app.js'
SUCCESS = {'passed', 'no_repair_adopted'}      # not failures: nothing to explain


def engine_reasons() -> set[str]:
    """Every stop reason the engines can emit, read from their source, so a new reason without words is caught."""
    found = set()
    for name in ('autonomous_core.py', 'modifier_engine.py'):
        text = (ROOT / 'omni_prod' / name).read_text(encoding='utf-8')
        found |= set(re.findall(r"stop_reason = '([a-z_]+)'", text))
        for pair in re.findall(r"'([a-z_]+)' if candidate == repo\s*\n\s*else '([a-z_]+)'", text):
            found |= set(pair)                  # the two-way ternary: unchanged / cycle
    return found


def js_stop_reason_line(build: dict, lang: str) -> str:
    source = APP.read_text(encoding='utf-8')
    translations = source[source.index('const T ='):source.index('const S =')]
    fn = re.search(r'function stopReasonLine\(.*?\n\}', source, re.S).group()
    js = (translations + f'\nconst S={{lang:{json.dumps(lang)}}};\nfunction t(k){{return T[S.lang][k];}}\n' + fn +
          f'\nconsole.log(JSON.stringify(stopReasonLine({json.dumps(build, ensure_ascii=False)})));')
    return json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)


def failed_build(reason):
    return {'status': 'failed', 'error_code': 'verification_failed', 'repair_rounds': 1,
            'evidence': {'repair_stop_reason': reason}}


class TheReasonReachesTheRecord(unittest.TestCase):
    def test_the_real_engine_stops_at_once_when_the_repository_did_not_change(self):
        rep, ex = _Repairer(['v0', 'v1', 'v2']), _Executor()
        result = _engine(rep, ex).build('p')
        self.assertEqual((result.status, result.stop_reason), ('failed', 'no_progress_repository_unchanged'))
        self.assertEqual(rep.calls, 1)                 # no second round after a no-op repair
        self.assertEqual(ex.runs, ['v0'])              # and nothing was sent to the sandbox again

    def test_the_worker_stores_the_engines_reason_on_the_failed_job(self):
        h = BuildHarness(verified=False)
        h.result.stop_reason = 'no_progress_repository_unchanged'
        self.assertEqual(h.run(), 'failed')
        self.assertEqual(h.final['evidence_json']['repair_stop_reason'], 'no_progress_repository_unchanged')

    def test_the_customer_view_keeps_the_reason(self):
        shown = strip_internal_economics({'repair_stop_reason': 'no_progress_repository_unchanged', 'provider_spend_usd': '1'})
        self.assertEqual(shown.get('repair_stop_reason'), 'no_progress_repository_unchanged')


@unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js stopReasonLine()')
class TheCustomerReadsTheReason(unittest.TestCase):
    def test_an_unchanged_repository_is_explained_in_the_customers_words(self):
        rep, ex = _Repairer(['v0', 'v1', 'v2']), _Executor()
        result = _engine(rep, ex).build('p')                      # the engine's own string, not a typed one
        self.assertEqual(js_stop_reason_line(failed_build(result.stop_reason), 'he'),
                         'התיקון האוטומטי נעצר: סבב התיקון האחרון לא שינה שום קובץ, ולכן סבב נוסף לא היה משנה דבר.')
        self.assertEqual(js_stop_reason_line(failed_build(result.stop_reason), 'en'),
                         'Automatic repair stopped: the last repair round changed no file, so another round would have changed nothing.')

    def test_every_reason_the_engines_can_emit_has_words_in_both_languages(self):
        reasons = engine_reasons() - SUCCESS
        self.assertTrue({'no_progress_repository_unchanged', 'max_repair_rounds', 'no_progress_same_failure'} <= reasons, reasons)
        source = APP.read_text(encoding='utf-8')
        tables = re.findall(r'repairStops:\{([^}]*)\}', source[source.index('const T ='):source.index('const S =')])
        self.assertEqual(len(tables), 2)
        for table in tables:
            for reason in reasons:
                self.assertIn(f'{reason}:', table, reason)
        for reason in sorted(reasons):
            for lang in ('he', 'en'):
                line = js_stop_reason_line(failed_build(reason), lang)
                self.assertTrue(line and reason not in line, (reason, lang, line))

    def test_a_reason_without_words_is_shown_not_hidden(self):
        self.assertEqual(js_stop_reason_line(failed_build('some_new_reason'), 'he'), 'התיקון האוטומטי נעצר: some_new_reason')

    def test_success_and_ready_builds_say_nothing(self):
        self.assertEqual(js_stop_reason_line(failed_build('passed'), 'he'), '')
        self.assertEqual(js_stop_reason_line({'status': 'ready', 'evidence': {'repair_stop_reason': 'passed'}}, 'he'), '')
        self.assertEqual(js_stop_reason_line({'status': 'failed', 'evidence': {}}, 'he'), '')


if __name__ == '__main__':
    unittest.main()
