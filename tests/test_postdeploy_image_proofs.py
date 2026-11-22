"""Warehouse 118 proven on a production build (the owner, 2026-11-22): the post-deploy paid stage records, on the page the
preview SERVES, that the image is a file the page references, that no data: is left in the HTML, and the weight against
the same page with its images inlined (what 118 replaced). The image is the real D5 hero file (BRAND_PACK)."""
import base64
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import postdeploy_checks as P

ROOT = Path(__file__).resolve().parents[1]
HERO = (ROOT / 'BRAND_PACK' / '148AI-logo-master-transparent.png').read_bytes()
PAGE = ('<!doctype html><html lang="he" dir="rtl"><head><title>סטודיו נועה</title></head><body>'
        '<header><h1>סטודיו נועה</h1></header><img src="assets/148ai-image-1.png" alt="המספרה מבפנים">'
        + '<p>תספורת, פן וצבע.</p>' * 40 + '</body></html>')


def serve(files):
    return lambda src: files.get(src, (404, 'text/html', b'not found'))


class TheThreeProofs(unittest.TestCase):
    def proofs(self, html, files):
        return {c: (ok, d) for c, ok, d in P.image_proofs(html, serve(files))}

    def test_a_file_image_passes_all_three_with_the_measured_ratio(self):
        out = self.proofs(PAGE, {'assets/148ai-image-1.png': (200, 'image/png', HERO)})
        self.assertTrue(out['118: the image is a file the page references'][0])
        self.assertTrue(out['118: no data: in the served HTML'][0])
        ok, detail = out['118: the HTML weight dropped by an order of magnitude']
        self.assertTrue(ok, detail)
        inlined = len(PAGE.encode()) + len('data:image/png;base64,' + base64.b64encode(HERO).decode()) \
            - len('assets/148ai-image-1.png')
        self.assertIn(f'{inlined} bytes', detail)                    # the counterfactual is exact, not estimated

    def test_an_inlined_image_fails_the_first_two(self):
        uri = 'data:image/png;base64,' + base64.b64encode(HERO).decode()
        anything = lambda src: (200, 'image/png', HERO)            # a server that answers every address
        out = {c: (ok, d) for c, ok, d in P.image_proofs(PAGE.replace('assets/148ai-image-1.png', uri), anything)}
        self.assertFalse(out['118: the image is a file the page references'][0])
        self.assertFalse(out['118: no data: in the served HTML'][0])

    def test_a_file_that_is_not_served_fails(self):
        out = self.proofs(PAGE, {})
        self.assertFalse(out['118: the image is a file the page references'][0])
        self.assertFalse(out['118: the HTML weight dropped by an order of magnitude'][0])

    def test_a_data_uri_left_elsewhere_in_the_html_fails_proof_two(self):
        css = '<style>.hero{background:url(data:image/png;base64,AAAA)}</style>'
        out = self.proofs(PAGE.replace('<head>', '<head>' + css),
                          {'assets/148ai-image-1.png': (200, 'image/png', HERO)})
        self.assertFalse(out['118: no data: in the served HTML'][0])

    def test_a_page_without_any_image_is_not_run_never_a_pass(self):
        out = P.image_proofs('<html><body><h1>x</h1></body></html>', serve({}))
        self.assertEqual([(c, ok) for c, ok, _ in out], [('118: image checks', None)])


class ThePaidPrompt(unittest.TestCase):
    def test_default_and_input(self):
        with mock.patch.dict(os.environ, {'POSTDEPLOY_PAID_PROMPT': ''}):
            self.assertEqual(P.paid_prompt(), P.PAID_PROMPT)
        with mock.patch.dict(os.environ, {'POSTDEPLOY_PAID_PROMPT': ' אתר תדמית למספרה עם תמונה ראשית '}):
            self.assertEqual(P.paid_prompt(), 'אתר תדמית למספרה עם תמונה ראשית')

    def test_the_workflow_passes_the_input_into_the_container(self):
        wf = (ROOT / '.github' / 'workflows' / 'postdeploy-checks.yml').read_text(encoding='utf-8')
        self.assertIn('POSTDEPLOY_PAID_PROMPT: ${{ inputs.paid_prompt }}', wf)
        self.assertIn('-e POSTDEPLOY_PAID_PROMPT -v', wf)


if __name__ == '__main__':
    unittest.main()


class ThePaidStageRecordsTheProofs(unittest.TestCase):
    """The real stage_paid_verify, collaborators stubbed as in test_postdeploy_paid_verify_missing_version: once the
    preview runs, the page it serves goes through the three proofs and they land in RESULTS."""

    def test_the_served_page_goes_through_the_proofs(self):
        from unittest.mock import patch
        build = {'status': 'ready', 'result_version_id': 'ver_1',
                 'evidence': {'browser_check': {'status': 'passed'}, 'product_review': [{'round': 1}]}}
        view = {'id': 'prv_1', 'status': 'RUNNING', 'preview_url': 'https://preview.example/p/', 'data_storage': 'persistent'}

        def api(method, path, *args):
            if '/events?' in path:
                return 200, {'events': [{'kind': 'info', 'message': 'synthetic'}] * 3}
            if '/previews/' in path:
                return 200, {**view, 'acceptance_status': 'PASS'}
            return 200, build

        def http(method, url, **kw):
            return 200, PAGE
        state = {'token': 't', 'paid_project': 'p', 'paid_build': 'b'}
        with patch.object(P, 'api', side_effect=api), patch.object(P, 'http', side_effect=http), \
                patch.object(P, 'reservation', return_value={'status': 'SETTLED'}), \
                patch.object(P, 'record_agent_graph'), patch.object(P, 'record_r2_artifact'), \
                patch.object(P, 'preview_launch', return_value=(view, None)), \
                patch.object(P, 'preview_header', return_value={'x-access': 'k'}), patch.object(P, 'preview_stop'), \
                patch.object(P, 'wait', return_value={'acceptance_status': 'PASS'}), \
                patch.object(P, 'fetch_bytes', return_value=(200, 'image/png', HERO)) as fetched:
            P.RESULTS.clear()
            P.stage_paid_verify(state)
        checks = {r['check']: r['ok'] for r in P.RESULTS}
        self.assertTrue(checks['118: the image is a file the page references'])
        self.assertTrue(checks['118: no data: in the served HTML'])
        self.assertTrue(checks['118: the HTML weight dropped by an order of magnitude'])
        self.assertEqual(fetched.call_args[0][0], 'https://preview.example/p/assets/148ai-image-1.png')
        self.assertEqual(fetched.call_args[0][1], {'x-access': 'k'})     # the image is fetched with the page's access


class TheQACapInput(unittest.TestCase):
    """One build's QA cap is a workflow input for the 118 proof run, never above the platform's 2.00 per-build cap."""

    def guard(self, value):
        import re
        import subprocess
        wf = (ROOT / '.github' / 'workflows' / 'postdeploy-checks.yml').read_text(encoding='utf-8')
        line = next(l for l in wf.splitlines() if "python3 -c 'import sys,decimal as d" in l)
        code = re.search(r"python3 -c '([^']+)'", line).group(1)
        return subprocess.run(['python3', '-c', code, value], capture_output=True).returncode

    def test_the_cap_accepts_up_to_two_dollars_and_nothing_else(self):
        self.assertEqual(self.guard('0.50'), 0)
        self.assertEqual(self.guard('2.00'), 0)
        for bad in ('2.01', '5', '0', '-1', 'abc', ''):
            self.assertNotEqual(self.guard(bad), 0, bad)

    def test_the_default_is_two_dollars(self):
        """The owner, 2026-11-22: a content site reserves about 2.00 at approval, so a 0.50 default blocked every
        content-site build, not only the 118 proof. The default and the fallback (a push has no inputs) are 2.00;
        the QA total stays 10."""
        wf = (ROOT / '.github' / 'workflows' / 'postdeploy-checks.yml').read_text(encoding='utf-8')
        self.assertIn('default: "2.00"', wf)
        self.assertEqual(wf.count('${QA_BUILD_MAX:-2.00}'), 2)
        self.assertNotIn('0.50', wf)
        self.assertIn('-e OMNI_QA_BUILD_MAX_USD=${QA_BUILD_MAX:-2.00}', wf)
        self.assertIn('-e OMNI_QA_BUDGET_TOTAL_USD=10 ', wf)
