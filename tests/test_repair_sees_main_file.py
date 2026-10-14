"""Crash run 37962802899: app.py (server + embedded page) exceeded the 16k
per-file limit, was left out of the repair prompt, and the repair model
answered that app.py was omitted."""
import unittest

from omni_prod.modifier_engine import focus_paths, repo_summary


def _contents(summary):
    return {f['path'] for f in summary['files'] if 'content' in f}


class RepairSeesMainFileTests(unittest.TestCase):
    def setUp(self):
        self.repo = {'.omni/project.json': '{}', 'app.py': 'x' * 30_000, 'test_app.py': 't' * 9_000,
                     'README.md': 'r' * 2_000, 'static/big.js': 'j' * 20_000}

    def test_entry_point_over_16k_is_included(self):
        self.assertIn('app.py', _contents(repo_summary(self.repo)))

    def test_files_named_in_failures_are_included_first(self):
        failures = [{'message': 'unit tests', 'evidence': 'static/big.js:12: TypeError'}]
        self.assertIn('static/big.js', focus_paths(self.repo, failures))
        self.assertIn('static/big.js', _contents(repo_summary(self.repo, failures)))

    def test_unrelated_large_files_still_respect_the_per_file_limit(self):
        self.assertNotIn('static/big.js', _contents(repo_summary(self.repo)))

    def test_total_budget_still_holds(self):
        repo = {f'm{i}.py': 'y' * 15_000 for i in range(10)}
        total = sum(len(f.get('content', '')) for f in repo_summary(repo)['files'])
        self.assertLessEqual(total, 64_000)


if __name__ == '__main__':
    unittest.main()
