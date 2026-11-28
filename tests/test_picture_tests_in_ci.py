"""#573 (visual plan S1-S3): the picture tests that need a browser skip loudly where there is none, and run where there is.

Found by the required `validate` job (141032356496): tests/test_item_pictures_in_library.py::InTheBrowser::
test_the_picture_measures_see_the_cards_pictures starts the platform's in-sandbox script as a process and did not check
for playwright first, so with no playwright it failed ("No module named 'playwright'") where its two siblings skipped.
Root cause: tests/test_item_pictures_in_library.py (that test) needs the same guard as the siblings. And no job that has
a browser ran either picture file, so a skip there would have been a pass nobody ever ran: browser-python's
`picture-measures` job runs both and fails on a skip.

The first test runs the real test with playwright made unimportable (a sitecustomize on the child's PYTHONPATH, so the
sandbox script's own process cannot import it either) and requires a skip, not a failure."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BLOCK = '''import sys
class _B:
    def find_spec(self, name, path=None, target=None):
        if name == "playwright" or name.startswith("playwright."):
            raise ModuleNotFoundError("No module named 'playwright'", name="playwright")
sys.meta_path.insert(0, _B())
'''
WORKFLOW = yaml.safe_load((ROOT / '.github' / 'workflows' / 'browser-python.yml').read_text(encoding='utf-8'))
JOB = WORKFLOW['jobs']['picture-measures']
STEPS = {s.get('name'): s for s in JOB['steps']}


class WithoutABrowser(unittest.TestCase):
    def test_every_browser_test_of_the_pictured_cards_skips_and_none_fails(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'sitecustomize.py').write_text(BLOCK, encoding='utf-8')
            xml = Path(d) / 'r.xml'
            env = dict(os.environ, PYTHONPATH=os.pathsep.join([d, os.environ.get('PYTHONPATH', '')]).strip(os.pathsep))
            p = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', f'--junitxml={xml}',
                                'tests/test_item_pictures_in_library.py', '-k', 'InTheBrowser'],
                               cwd=ROOT, env=env, capture_output=True, text=True, timeout=240)
            cases = list(ET.parse(xml).getroot().iter('testcase'))
        self.assertEqual(len(cases), 3, p.stdout[-800:])
        bad = [c.get('name') for c in cases if c.find('failure') is not None or c.find('error') is not None]
        self.assertEqual(bad, [], p.stdout[-800:])
        self.assertEqual(sum(c.find('skipped') is not None for c in cases), 3)


class TheJobThatHasABrowser(unittest.TestCase):
    def test_runs_both_picture_files_on_every_pull_request_and_a_skip_fails_it(self):
        self.assertIn('pull_request', WORKFLOW.get('on') or WORKFLOW.get(True))
        run = STEPS['Picture tests']['run'].split()
        self.assertIn('tests/test_visual_picture_measures.py', run)
        self.assertIn('tests/test_item_pictures_in_library.py', run)
        guard = STEPS['No test may be skipped']
        self.assertEqual(guard['if'], 'always()')
        self.assertIn("ET.parse('pictures.xml')", guard['run'])
        self.assertIn('sys.exit(1 if skipped or failed or not cases else 0)', guard['run'])

    def test_every_control_whose_expected_test_needs_chromium_is_declared_browser_and_run_there(self):
        # #573, negative-controls (4): visual-s1 NC1, NC4-NC8 were DID NOT RUN, because their expected tests skip in the
        # shards that have no browser. Each is `envs: browser` and runs in this job, with NC_SCOPE=declared.
        step = STEPS['Negative controls (browser)']
        self.assertEqual(step['env']['NC_ENV'], 'browser')
        want = {'hero_photo_led': ['NC1', 'NC4', 'NC5', 'NC6', 'NC7', 'NC8'],
                'visual_picture_measures': ['NC1', 'NC3', 'NC4', 'NC5', 'NC8', 'NC9', 'NC10', 'NC11', 'NC12'],
                'item_pictures_in_library': ['NC11'], 'hero_overlay_stacking': ['NC1']}
        for spec, ids in want.items():
            self.assertIn(f'NC_SCOPE=declared python scripts/run_negative_controls.py {spec};', step['run'], spec)
            controls = json.loads((ROOT / 'tests' / 'negative_controls' / f'{spec}.json').read_text(encoding='utf-8'))['controls']
            self.assertEqual([c['id'] for c in controls if c.get('envs') == ['browser']], ids, spec)

    def test_the_steps_fit_inside_the_job(self):
        self.assertLessEqual(sum(s.get('timeout-minutes', 0) for s in JOB['steps']) + 1, JOB['timeout-minutes'])


if __name__ == '__main__':
    unittest.main()
