"""The asset-marker gate reads what the browser loads, not the generated app's own tests (production 2026-11-25).

The owner's "148 דלתות" (prj_XtkC8IA8C2TwUQ) failed twice that night, read-only from build_jobs:
  bld_4de8e7e431124ca096d5e4baaf2ea226  3 repair rounds  ASSET_MARKER_UNRESOLVED: tests/test_site.py: src "148ai-asset://"
  bld_d3222f81e2ae491686d07a272434348d  4 repair rounds  ASSET_MARKER_UNRESOLVED: tests/test_app.py: src "148ai-asset://"
Both are the only ASSET_MARKER_UNRESOLVED failures of the last 14 days, and both name a test file. The address is the
bare scheme: the generated test asserted that no 148ai-asset:// address is left in the page, and the gate, which reads
every .py file because a page can be served from app.py, read that assertion as a broken image. The repair could not
fix what was not broken, and the customer was told that a picture on the site did not load.

The real gate (asset_markers.AssetMarkerExecutor) over the sandbox double of tests/test_contract_prompt_readers.py,
which records and passes: the decision under test is the gate's own."""
import unittest

from omni_prod import asset_markers as A
from tests.test_contract_prompt_readers import MARKER, PHOTO_URI, _Recording, hero

# what the generated tests said, in the shape the failure message quotes (src "148ai-asset://")
PRODUCTION_TEST = ("from app import render\n\n\ndef test_no_placeholder_left():\n"
                   "    html = render()\n    assert '148ai-asset://' not in html\n")


def run(repository):
    return A.AssetMarkerExecutor(_Recording()).execute(repository=repository, spec='s')


class TheProductionFailure(unittest.TestCase):
    def test_a_clean_page_with_the_generated_tests_passes(self):
        for test_path in ('tests/test_site.py', 'tests/test_app.py'):
            with self.subTest(test_path=test_path):
                report = run({'index.html': hero(PHOTO_URI), test_path: PRODUCTION_TEST,
                              'app.py': 'HTML = """' + hero(PHOTO_URI) + '"""\n'})
                self.assertTrue(report.passed, report.failures)
                self.assertEqual(A.unresolved({test_path: PRODUCTION_TEST}), [])

    def test_the_page_itself_is_still_read_beside_its_tests(self):
        report = run({'index.html': hero(MARKER), 'tests/test_site.py': PRODUCTION_TEST})
        self.assertFalse(report.passed)
        [f] = report.failures
        self.assertIn(f'{A.CODE}: index.html: src "{MARKER}"', f.message)
        self.assertNotIn('tests/test_site.py', f.message)

    def test_a_page_served_from_app_py_is_still_read(self):
        self.assertFalse(run({'app.py': 'HTML = """' + hero(MARKER) + '"""\n',
                              'tests/test_app.py': PRODUCTION_TEST}).passed)


class WhatIsATestFile(unittest.TestCase):
    def test_test_directories_and_names_are_not_read(self):
        for path in ('tests/test_site.py', 'tests/helpers.py', 'test/page.html', 'src/__tests__/hero.js',
                     'spec/hero.js', 'test_site.py', 'site_test.py', 'conftest.py', 'web/hero.test.js',
                     'web/hero.spec.ts', 'web/hero.test.mjs', 'web/Hero.Spec.TSX'):
            with self.subTest(path=path):
                self.assertTrue(A.is_test_file(path))
                self.assertEqual(A.unresolved({path: f'<img src="{MARKER}">'}), [])

    def test_served_files_with_test_like_words_are_still_read(self):
        # a near name is not a test: a page about testimonials, a "latest" folder, tests.html, attest.py, contest.css
        for path in ('testimonials.html', 'latest/index.html', 'tests.html', 'attest.py', 'contest.css',
                     'static/testing.js', 'app.py', 'index.html'):
            with self.subTest(path=path):
                self.assertFalse(A.is_test_file(path))
                self.assertEqual(A.unresolved({path: f'<img src="{MARKER}">'}), [(path, MARKER)])


if __name__ == '__main__':
    unittest.main()
