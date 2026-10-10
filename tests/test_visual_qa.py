"""Visual QA (Production Assurance v2 §6; issue #6 Visual QA)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from omni_prod.autonomous_core import ExecutionReport
from omni_prod.visual_qa import SCRIPT, VISUAL_FAILURE_ID, VisualQAExecutor, parse

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'visual'
CHROMIUM = os.environ.get('OMNI_CHROMIUM') or next((p for p in ('/opt/pw-browsers/chromium', '/usr/bin/chromium')
                                                     if os.path.exists(p)), None)
try:
    import playwright  # noqa: F401
    HAVE_BROWSER = CHROMIUM is not None
except ImportError:
    HAVE_BROWSER = False


def _stdout(findings, shot=b'\xff\xd8jpeg'):
    import base64
    return ('OMNI_VISUAL_SHOT ' + base64.b64encode(shot).decode() + '\n' +
            'OMNI_VISUAL_QA ' + json.dumps({'viewport': 'x', 'findings': findings, 'controls': 3, 'text_elements': 5}))


class _Inner:
    def __init__(self, findings):
        self.findings, self.calls = findings, []

    def execute(self, **k):
        return ExecutionReport(True, (), '')

    def _run(self, repo, argv, tag, profile=None):
        self.calls.append((argv[-1], profile))
        return {'returncode': 0, 'stdout': _stdout(self.findings.get(argv[-1], [])), 'stderr': ''}


class ExecutorTests(unittest.TestCase):
    def test_shadow_mode_records_but_does_not_block(self):
        inner = _Inner({'mobile': [{'kind': 'h_overflow', 'detail': 'page width 600px', 'at': ''}]})
        ex = VisualQAExecutor(inner)
        stored = {}
        ex.screenshot_sink = lambda vp, jpg: stored.setdefault(vp, f'k/{vp}.jpg')
        with patch.dict(os.environ, {'OMNI_VISUAL_QA_ENFORCE': ''}):          # explicit shadow mode
            self.assertTrue(ex.execute(repository={}, spec=None).passed)
        self.assertEqual([c[0] for c in inner.calls], ['desktop', 'mobile'])
        self.assertTrue(all(c[1] == 'browser' for c in inner.calls))
        self.assertEqual(ex.last_visual['status'], 'FINDINGS')
        self.assertEqual(ex.last_visual['mode'], 'shadow')
        self.assertEqual(ex.last_visual['viewports']['mobile']['counts'], {'h_overflow': 1})
        self.assertEqual(ex.last_visual['viewports']['desktop']['screenshot_key'], 'k/desktop.jpg')

    def test_enforced_rule_blocks_with_a_repairable_failure(self):
        inner = _Inner({'mobile': [{'kind': 'h_overflow', 'detail': 'page width 600px', 'at': ''}]})
        with patch.dict(os.environ, {'OMNI_VISUAL_QA_ENFORCE': 'h_overflow,unknown_rule'}):
            report = VisualQAExecutor(inner).execute(repository={}, spec=None)
        self.assertFalse(report.passed)
        self.assertEqual(report.failures[0].acceptance_id, VISUAL_FAILURE_ID)
        self.assertIn('(mobile) h_overflow', report.failures[0].message)

    def test_layout_rules_block_by_default_but_contrast_does_not(self):
        env = dict(os.environ); env.pop('OMNI_VISUAL_QA_ENFORCE', None)
        with patch.dict(os.environ, env, clear=True):
            contrast = _Inner({'desktop': [{'kind': 'low_contrast', 'detail': '4.1:1', 'at': 'button'}]})
            self.assertTrue(VisualQAExecutor(contrast).execute(repository={}, spec=None).passed)
            overflow = _Inner({'mobile': [{'kind': 'h_overflow', 'detail': '600px', 'at': ''}]})
            self.assertFalse(VisualQAExecutor(overflow).execute(repository={}, spec=None).passed)

    def test_no_runner_is_not_run_not_pass(self):
        ex = VisualQAExecutor(SimpleNamespace(execute=lambda **k: ExecutionReport(True, (), '')))
        self.assertTrue(ex.execute(repository={}, spec=None).passed)
        self.assertEqual(ex.last_visual['status'], 'NOT_RUN')

    def test_parse_survives_a_truncated_screenshot(self):
        report, shot = parse('OMNI_VISUAL_SHOT abc$$$\nOMNI_VISUAL_QA {"findings": []}')
        self.assertEqual(report, {'findings': []})
        self.assertIsNone(shot)


@unittest.skipUnless(HAVE_BROWSER, 'playwright + chromium not available')
class RealBrowserTests(unittest.TestCase):
    """Runs the exact in-sandbox script against two fixture products."""

    def _run(self, app, viewport, port):
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(FIXTURES / f'{app}_app.py', Path(d) / 'app.py')
            (Path(d) / '.omni').mkdir()
            (Path(d) / '.omni' / 'project.json').write_text(json.dumps(
                {'port': port, 'start': [sys.executable, 'app.py'], 'health_path': '/'}))
            proc = subprocess.run([sys.executable, '-c', SCRIPT, viewport], cwd=d, capture_output=True, text=True,
                                  timeout=90, env=dict(os.environ, OMNI_CHROMIUM=CHROMIUM))
        report, shot = parse(proc.stdout)
        self.assertIsNotNone(report, proc.stderr[-800:])
        return {f['kind'] for f in report['findings']}, shot

    def test_a_clean_rtl_page_has_no_findings_on_desktop_or_mobile(self):
        for vp, port in (('desktop', 18731), ('mobile', 18732)):
            kinds, shot = self._run('good', vp, port)
            self.assertEqual(kinds, set(), vp)
            self.assertTrue(shot and shot[:2] == b'\xff\xd8', vp)          # a real JPEG

    def test_a_broken_page_triggers_every_planted_defect(self):
        kinds, _ = self._run('bad', 'mobile', 18733)
        for k in ('no_mobile_viewport', 'h_overflow', 'missing_lang', 'rtl_mismatch', 'small_touch', 'unlabelled_field',
                  'unnamed_control', 'positive_tabindex', 'overlap', 'broken_image', 'low_contrast', 'console_error'):
            self.assertIn(k, kinds)


if __name__ == '__main__':
    unittest.main()
