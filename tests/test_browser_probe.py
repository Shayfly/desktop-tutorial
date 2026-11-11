"""Real-browser check (directive 2026-10-09 §17; founder's library 2026-10-08:
"nothing responds" / messages vanish after the first one)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from omni_prod.autonomous_core import ExecutionReport
from omni_prod.browser_fixtures import fixture_repository
from omni_prod.browser_probe import BROWSER_FAILURE_ID, PROBE, BrowserFlowExecutor, parse_probe_output


class _Inner:
    def __init__(self, stdout='', exc=None, profile_ok=True):
        self.stdout, self.exc, self.profile_ok, self.calls = stdout, exc, profile_ok, []

    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'log')

    def _run(self, repository, argv, build_id, profile='default'):
        self.calls.append((argv[:2], build_id, profile))
        if self.exc:
            raise self.exc
        return {'returncode': 0, 'stdout': self.stdout, 'stderr': ''}


def _out(findings, forms=()):
    return 'noise\nOMNI_BROWSER_PROBE ' + json.dumps({'findings': findings, 'forms': list(forms)})


class ExecutorTests(unittest.TestCase):
    def test_blocking_finding_becomes_repairable_browser_failure(self):
        inner = _Inner(_out([{'kind': 'feedback_disappears', 'message': "form 'f': second submit showed nothing"}]))
        ex = BrowserFlowExecutor(inner)
        report = ex.execute(repository={}, spec=None)
        self.assertFalse(report.passed)
        self.assertEqual(report.failures[0].acceptance_id, BROWSER_FAILURE_ID)
        self.assertIn('second submit showed nothing', report.failures[0].message)
        self.assertEqual(inner.calls[0][2], 'browser')
        self.assertEqual(ex.last_probe['status'], 'failed')

    def test_clean_probe_passes_and_is_recorded(self):
        ex = BrowserFlowExecutor(_Inner(_out([], [{'form': 'f'}])))
        self.assertTrue(ex.execute(repository={}, spec=None).passed)
        self.assertEqual(ex.last_probe, {'status': 'passed', 'forms': 1, 'findings': []})

    def test_unavailable_browser_is_recorded_not_passed(self):
        for inner in (_Inner(exc=RuntimeError('no image')), _Inner(stdout='crash, no json')):
            ex = BrowserFlowExecutor(inner)
            r = ex.execute(repository={}, spec=None)          # T4: "could not verify" is never "verified"
            self.assertFalse(r.passed)
            self.assertEqual([f.acceptance_id for f in r.failures], ['BROWSER_UNVERIFIED'])
            self.assertEqual(ex.last_probe['status'], 'unavailable')

    def test_disabled_does_not_run(self):
        inner = _Inner(_out([{'kind': 'page_error', 'message': 'x'}]))
        self.assertTrue(BrowserFlowExecutor(inner, enabled=False).execute(repository={}, spec=None).passed)
        self.assertEqual(inner.calls, [])

    def test_parse_takes_the_marker_line(self):
        self.assertEqual(parse_probe_output(_out([]))['findings'], [])
        self.assertIsNone(parse_probe_output('OMNI_BROWSER_PROBE {broken'))


def _chromium():
    for path in (os.environ.get('OMNI_CHROMIUM', ''), '/opt/pw-browsers/chromium', '/usr/bin/chromium'):
        if path and Path(path).exists():
            return path
    return None


def _has_playwright():
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_chromium() and _has_playwright(), 'needs Chromium and Playwright')
class RealBrowserTests(unittest.TestCase):
    """Runs PROBE exactly as the sandbox does, against fixture products."""

    def _probe(self, port, **kw):
        with tempfile.TemporaryDirectory() as d:
            for rel, content in fixture_repository(port=port, **kw).items():
                p = Path(d) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')
            manifest = json.loads((Path(d) / '.omni/project.json').read_text())
            manifest['start'] = [sys.executable, 'app.py']
            (Path(d) / '.omni/project.json').write_text(json.dumps(manifest))
            r = subprocess.run([sys.executable, '-c', PROBE], cwd=d, capture_output=True, text=True, timeout=120,
                               env={**os.environ, 'OMNI_CHROMIUM': _chromium()})
            out = parse_probe_output(r.stdout)
            self.assertIsNotNone(out, r.stdout[-500:] + r.stderr[-1500:])
            return {f['kind'] for f in out['findings']}

    def test_working_product_passes(self):
        self.assertEqual(self._probe(8791), set())

    def test_message_hidden_after_first_use_is_caught(self):
        self.assertEqual(self._probe(8792, feedback_bug=True), {'feedback_disappears'})

    def test_dead_form_is_caught(self):
        self.assertIn('dead_form', self._probe(8793, dead_form=True))

    def test_javascript_error_is_caught(self):
        self.assertIn('page_error', self._probe(8794, js_error=True))


if __name__ == '__main__':
    unittest.main()
