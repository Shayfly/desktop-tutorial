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
        r = ex.execute(repository={}, spec=None)              # T4: NOT_RUN is not PASS (and never was meant to be)
        self.assertFalse(r.passed)
        self.assertEqual([f.acceptance_id for f in r.failures], ['VISUAL_UNVERIFIED'])
        self.assertEqual(ex.last_visual['status'], 'NOT_RUN')

    def test_parse_survives_a_truncated_screenshot(self):
        report, shot = parse('OMNI_VISUAL_SHOT abc$$$\nOMNI_VISUAL_QA {"findings": []}')
        self.assertEqual(report, {'findings': []})
        self.assertIsNone(shot)


def _free_port() -> int:
    """A port the OS says is free now. The tests passed fixed ports (18731-18739); two negative controls of
    repair_converge_offscreen running at once (NC_JOBS=2) then started their pages on the same port and refused each
    other (run 45860673027: ERR_CONNECTION_REFUSED at 127.0.0.1:18733). The fixed numbers stay as the tests'
    arguments; this replaces them at the one place a page is started."""
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@unittest.skipUnless(HAVE_BROWSER, 'playwright + chromium not available')
class RealBrowserTests(unittest.TestCase):
    """Runs the exact in-sandbox script against two fixture products."""

    def _run(self, app, viewport, port):
        port = _free_port()
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

    # bld_cb2d1b90a90f430c98603d14f8afa1a8 (2026-11-24): every round failed with "page width 11439px > viewport 1440px",
    # "page width 10389px > viewport 1560px" and "no meta viewport", with no element named. One skip link at
    # left:-9999px on a right-to-left page WITH a meta viewport gives exactly those numbers.
    OFFSCREEN_PAGE = ('<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="utf-8">'
                      '<meta name="viewport" content="width=device-width,initial-scale=1"><title>מספרה</title><style>'
                      'body{margin:0;font-family:sans-serif;color:#111;background:#fff}'
                      '.skip-link{position:absolute;left:-9999px;top:0;background:#111;color:#fff;padding:8px}'
                      '.skip-link:focus{left:0}main{padding:16px}</style></head><body>'
                      '<a class="skip-link" href="#main">דלג לתוכן</a><main id="main"><h1>מספרה בעיר</h1>'
                      '<p>תורים בטלפון ובוואטסאפ</p></main></body></html>')

    def _findings(self, page, viewport, port):
        port = _free_port()
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(FIXTURES / 'offscreen_app.py', Path(d) / 'app.py')
            (Path(d) / 'page.html').write_text(page, encoding='utf-8')
            (Path(d) / '.omni').mkdir()
            (Path(d) / '.omni' / 'project.json').write_text(json.dumps(
                {'port': port, 'start': [sys.executable, 'app.py'], 'health_path': '/'}))
            proc = subprocess.run([sys.executable, '-c', SCRIPT, viewport], cwd=d, capture_output=True, text=True,
                                  timeout=90, env=dict(os.environ, OMNI_CHROMIUM=CHROMIUM))
        report, _ = parse(proc.stdout)
        self.assertIsNotNone(report, proc.stderr[-800:])
        return {f['kind']: f for f in report['findings'] if f['kind'] in ('h_overflow', 'no_mobile_viewport')}

    def test_the_element_that_widens_the_page_is_named(self):
        desktop = self._findings(self.OFFSCREEN_PAGE, 'desktop', 18734)
        self.assertEqual(desktop['h_overflow']['at'], 'a.skip-link')
        self.assertTrue(desktop['h_overflow']['detail'].startswith(
            'page width 11439px > viewport 1440px; it sticks out at x -9999..'), desktop['h_overflow']['detail'])
        mobile = self._findings(self.OFFSCREEN_PAGE, 'mobile', 18735)
        self.assertEqual(mobile['h_overflow']['at'], 'a.skip-link')
        self.assertTrue(mobile['h_overflow']['detail'].startswith('page width 10389px > viewport 390px'),
                        mobile['h_overflow']['detail'])

    def test_a_page_with_a_meta_viewport_is_never_called_one_without(self):
        mobile = self._findings(self.OFFSCREEN_PAGE, 'mobile', 18736)
        self.assertNotIn('no_mobile_viewport', mobile)                         # zoomed out by the overflow, not by it
        bare = self.OFFSCREEN_PAGE.replace('<meta name="viewport" content="width=device-width,initial-scale=1">', '')
        self.assertTrue(self._findings(bare, 'mobile', 18737)['no_mobile_viewport']['detail']
                        .startswith('no meta viewport in the page'))

    def test_the_platforms_rewrite_leaves_no_overflow(self):
        from omni_prod.offscreen import rewrite
        fixed, done = rewrite({'index.html': self.OFFSCREEN_PAGE})
        self.assertEqual(done, ['index.html:1 left -9999px'])
        for vp, port in (('desktop', 18738), ('mobile', 18739)):
            self.assertEqual(self._findings(fixed['index.html'], vp, port), {}, vp)

    def test_the_rewritten_skip_link_still_shows_when_focused(self):
        from playwright.sync_api import sync_playwright
        from omni_prod.offscreen import rewrite
        page_html = rewrite({'index.html': self.OFFSCREEN_PAGE})[0]['index.html']
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROMIUM, args=['--no-sandbox', '--disable-dev-shm-usage'])
            page = b.new_context(viewport={'width': 1440, 'height': 900}).new_page()
            page.set_content(page_html)
            hidden = page.evaluate("() => document.querySelector('.skip-link').getBoundingClientRect().width")
            page.keyboard.press('Tab')
            shown = page.evaluate("() => { const e = document.activeElement, r = e.getBoundingClientRect();"
                                  " return [e.className, r.width, r.left >= 0 && r.right <= innerWidth]; }")
            b.close()
        self.assertLessEqual(hidden, 1)
        self.assertEqual(shown[0], 'skip-link')
        self.assertGreater(shown[1], 20)
        self.assertTrue(shown[2])


if __name__ == '__main__':
    unittest.main()
