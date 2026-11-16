"""The fast suite never runs a file that needs packages this container lacks or that touches the environment
(the owner, 2026-11-15 22:50). The list is measured (tests/fast_suite.txt); this test refuses a list that drifted."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEAVY = re.compile(r'fastapi|psycopg|boto3|botocore|TestClient')
ENV = re.compile(r'os\.environ|setenv|getenv|subprocess|patch\.dict\(\s*os')


def listed() -> list[str]:
    lines = (ROOT / 'tests' / 'fast_suite.txt').read_text(encoding='utf-8').splitlines()
    return [l.strip() for l in lines if l.strip() and not l.lstrip().startswith('#')]


class TheFastSuite(unittest.TestCase):
    def test_it_lists_existing_test_files_once(self):
        files = listed()
        self.assertGreater(len(files), 0)
        self.assertEqual(len(files), len(set(files)))
        for f in files:
            self.assertTrue((ROOT / f).is_file(), f)
            self.assertRegex(f, r'^tests/(\w+/)?test_\w+\.py$')

    def test_no_file_needs_fastapi_psycopg_or_boto(self):
        bad = [f for f in listed() if HEAVY.search((ROOT / f).read_text(encoding='utf-8'))]
        self.assertEqual(bad, [], 'these need packages absent here; they belong to the full suite')

    def test_no_file_touches_the_environment(self):
        bad = [f for f in listed() if ENV.search((ROOT / f).read_text(encoding='utf-8'))]
        self.assertEqual(bad, [])

    def test_the_list_is_re_measured_when_the_suite_changed_by_100_files(self):
        head = (ROOT / 'tests' / 'fast_suite.txt').read_text(encoding='utf-8')
        measured = int(re.search(r'since this date \((\d+) here\)', head).group(1))
        now = len(list((ROOT / 'tests').glob('test_*.py'))) + len(list((ROOT / 'tests').glob('*/test_*.py')))
        # both ways (the owner, 23:43): 150 files deleted leaves the list "valid" while it covers less
        self.assertLess(abs(now - measured), 100,
                        f'{now} test files, measured at {measured}: re-measure tests/fast_suite.txt')

    def test_it_never_lists_itself_out_of_the_full_suite(self):
        self.assertNotIn('tests/test_fast_suite.py', listed())   # its own patterns spell the forbidden words


if __name__ == '__main__':
    unittest.main()
