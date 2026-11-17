"""G-APPLE's render probe in a real browser (the owner, 2026-11-17): real pages are served by a real server and opened
in headless Chromium at 390, 768, 1440 and 320, exactly as the sandbox's browser profile would; the request passes the
real sandbox request policy first. Without a local Chromium these are NOT_RUN (skipped, said)."""
import os
import unittest

from omni_prod.g_apple import render as R
from omni_prod.sandbox_script import staged_script
from tests.test_g_apple import CONTRACT, page
from tests.test_game_runtime import HAVE_BROWSER, LocalBrowserSandbox, MANIFEST, _APP

NESTED = os.environ.get('OMNI_M4_ACCEPTANCE_W_NESTED') == '1'
LONG = 'בית הקפה השכונתי שלנו פתוח כל יום מהבוקר ועד הערב ומגיש קפה טרי ומאפים מהתנור. ' * 4
GOOD = page('p{max-width:52ch;line-height:1.5;margin:0 0 var(--space-16)} main{padding:var(--space-24)} '
            '.btn{display:inline-block;min-height:48px;box-sizing:border-box}',
            body=f'<main><h1>קפה נחמה</h1><p>{LONG}</p><a class="btn" href="tel:035551234">התקשרו אלינו</a></main>')


def measure(html, width):
    repo = {'app.py': _APP % html, '.omni/project.json': MANIFEST}
    staged, argv = staged_script(repo, 'apple_render', R.PROBE, str(width))
    out = LocalBrowserSandbox()._run(staged, argv, f'apple-{width}', profile='browser')
    measured = R.parse(out['stdout'])
    assert measured is not None, out['stderr'][-600:]
    return measured, sorted({f['code'] for f in R.findings(measured)})


@unittest.skipUnless(HAVE_BROWSER, 'NOT_RUN: no local Chromium and Playwright')
@unittest.skipIf(NESTED, 'real browser: run once in the main suite, not again in the time-bounded nested run')
class InARealBrowser(unittest.TestCase):
    def test_a_page_that_keeps_the_rules_has_no_finding_at_any_of_the_four_widths(self):
        for width in R.WIDTHS:
            measured, codes = measure(GOOD, width)
            self.assertEqual(codes, [], (width, measured['findings']))
            self.assertEqual(len(measured['screenshot']['sha256']), 64)
            self.assertGreater(measured['screenshot']['bytes'], 1000)

    def test_each_measured_rule(self):
        cases = {
            'H_SCROLL': (GOOD.replace('<main>', '<main><div style="width:1900px">x</div>'), 320),
            'CONTROL_UNDER_44': (GOOD.replace('min-height:48px', 'min-height:0;padding:0;font-size:var(--text-12)'), 390),
            'OFF_GRID': (GOOD.replace('main{padding:var(--space-24)}', 'main{padding:13px}'), 768),
            'MEASURE': (GOOD.replace('max-width:52ch', 'max-width:none'), 1440),
            'CLIPPED_TEXT': (GOOD.replace('<h1>', '<h1 style="width:60px;overflow:hidden;white-space:nowrap">'), 390),
        }
        for code, (html, width) in cases.items():
            _, codes = measure(html, width)
            self.assertIn(code, codes, (code, width))

    def test_a_long_real_name_is_tried_and_a_layout_that_breaks_on_it_is_found(self):
        brittle = GOOD.replace('.btn{display:inline-block', '.btn{white-space:nowrap;display:inline-block')
        _, codes = measure(brittle, 320)
        self.assertIn('STRING_60', codes)
        measured, _ = measure(GOOD, 320)
        self.assertNotIn('STRING_60', [f['code'] for f in measured['findings']])

    def test_line_length_is_judged_on_wide_screens_only(self):
        wide = GOOD.replace('max-width:52ch', 'max-width:none')
        self.assertNotIn('MEASURE', measure(wide, 390)[1])
        self.assertIn('MEASURE', measure(wide, 1440)[1])


class TheBounds(unittest.TestCase):
    def test_four_widths_and_every_loop_is_bounded(self):
        self.assertEqual(sorted(R.WIDTHS), [320, 390, 768, 1440])
        self.assertEqual((R.MIN_CONTROL, R.MEASURE_MIN, R.MEASURE_MAX), (44, 55, 75))
        self.assertLessEqual(R.MAX_ELEMENTS, 100)
        self.assertIn('if (++n > maxEl', R.PROBE)

    def test_a_server_that_never_started_and_a_malformed_report_are_said(self):
        self.assertEqual([f['code'] for f in R.findings({'width': 390, 'started': False, 'findings': []})], ['NOT_STARTED'])
        self.assertIsNone(R.parse('no report here'))
        self.assertIsNone(R.parse('APPLE-RENDER {"width": 390}'))
        self.assertEqual(R.findings({'width': 390, 'started': True, 'findings': [{'code': 'INVENTED', 'why': 'x'}]}), [])


if __name__ == '__main__':
    unittest.main()
