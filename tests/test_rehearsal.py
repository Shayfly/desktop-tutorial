"""Rehearsal report and runtime-environment rules (2026-10-08)."""
import unittest

from omni_prod.dependency_policy import GENERATION_CONSTRAINTS
from omni_prod.rehearsal import annotations
from omni_prod.remote_sandbox import _output_tail


class RehearsalTests(unittest.TestCase):
    def test_annotations_are_escaped_and_bounded(self):
        lines = annotations({'outcome': 'failed', 'quality': {'score': 70, 'passed': False},
                             'failures': [{'id': f'A{i}', 'message': 'm', 'evidence': '50%\nx'} for i in range(9)]})
        self.assertLessEqual(len(lines), 10)
        self.assertTrue(all('\n' not in l for l in lines))
        self.assertIn('50%25%0Ax', lines[-1])

    def test_failure_evidence_includes_stdout(self):
        # bld_760c823b822643ebb0512f05d43693aa: pytest wrote the error to stdout.
        tail = _output_tail({'stdout': 'sqlite3.OperationalError: unable to open database file', 'stderr': ''})
        self.assertIn('unable to open database file', tail)

    def test_generator_is_told_the_repository_is_read_only(self):
        for needle in ('READ-ONLY', 'DATA_DIR', 'tmp_path', 'Python 3.11', 'free port'):
            self.assertIn(needle, GENERATION_CONSTRAINTS)


if __name__ == '__main__':
    unittest.main()
