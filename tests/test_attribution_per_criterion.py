"""Warehouse 106 (released by the owner 2026-11-15): a failing test is attributed to the criterion whose verify command
names it, and to no other.

The finding (bld_2a75e300, 2026-11-02; PR #210): one verify entry `python -m pytest -q` carried A1..A8, so
"1 failed, 2 passed" failed all eight criteria and a partial fix could never show as progress. The engine attributes a
failed verify command to every acceptance id that command carries -- so the cure is one verify entry per criterion
(#210 teaches the generator that shape and adds the pre-flight check). This test proves the attribution on the real
remote executor: RemoteSandboxRepositoryExecutor.execute, its real _run (snapshot and command policy, signed body),
and the stub runner from tests.test_sandbox_callers_real_policy that really runs pytest on the snapshot.

Open spec question for Michael, not decided here: a criterion that NO verify command covers is reported today as a
FAILED criterion ("no verification command covers this acceptance criterion", project_manifest.uncovered_acceptance_failures,
Golden E2E #1) so the repair loop adds the missing test. Item 106's acceptance text says such a criterion is not_run.
The behaviour below documents what runs today.
"""
from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor
from tests.test_sandbox_callers_real_policy import StubRunner

APP = 'def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b + 1   # the defect: A2 fails, A1 passes\n'
TESTS = ('import sys, os\nsys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n'
         'from app import add, sub\n\n\ndef test_a1_add():\n    assert add(2, 2) == 4\n\n\n'
         'def test_a2_sub():\n    assert sub(5, 3) == 2\n')
SPEC = SimpleNamespace(acceptance=(SimpleNamespace(id='A1', text='adds'), SimpleNamespace(id='A2', text='subtracts'),
                                   SimpleNamespace(id='A3', text='no test was written for this one')), requirements=())
PREVIEW = {'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'], 'port': 8000,
           'health_path': '/'}


def repo(verify: list[dict]) -> dict:
    return {'app.py': APP, 'tests/__init__.py': '', 'tests/test_app.py': TESTS,
            '.omni/project.json': json.dumps({**PREVIEW, 'build': [], 'verify': verify})}


def execute(repository):
    runner = StubRunner()
    ex = RemoteSandboxRepositoryExecutor(RemoteSandboxConfig('http://sandbox.invalid', 'x' * 40), urlopen=runner)
    return ex.execute(repository=repository, spec=SPEC), runner


class AttributionPerCriterion(unittest.TestCase):
    def test_one_verify_entry_per_criterion_fails_only_the_criterion_whose_test_failed(self):
        report, runner = execute(repo([
            {'name': 'A1 adds', 'argv': ['python', '-m', 'pytest', '-q', 'tests/test_app.py::test_a1_add'], 'acceptance_ids': ['A1']},
            {'name': 'A2 subtracts', 'argv': ['python', '-m', 'pytest', '-q', 'tests/test_app.py::test_a2_sub'], 'acceptance_ids': ['A2']},
        ]))
        self.assertFalse(report.passed)
        by_id = {}
        for f in report.failures:
            by_id.setdefault(f.acceptance_id, []).append(f.message)
        self.assertEqual(set(by_id), {'A2', 'A3'})                         # A1 keeps its own result: passed
        self.assertIn('remote verification failed', by_id['A2'][0])
        self.assertIn('test_a2_sub', ' '.join(by_id['A2']) + ' '.join(f.evidence or '' for f in report.failures if f.acceptance_id == 'A2'))
        self.assertEqual(report.tests_executed, 2)                          # both commands really ran pytest
        self.assertEqual(len(runner.requests), 2)
        # today: a criterion no command covers is a FAILED criterion with this exact reason (see the module docstring)
        self.assertEqual(by_id['A3'], ['no verification command covers this acceptance criterion'])

    def test_one_command_for_every_criterion_fails_them_all_the_finding_of_bld_2a75e300(self):
        report, _ = execute(repo([
            {'name': 'unit tests', 'argv': ['python', '-m', 'pytest', '-q'], 'acceptance_ids': ['A1', 'A2', 'A3']},
        ]))
        self.assertFalse(report.passed)
        self.assertEqual({f.acceptance_id for f in report.failures}, {'A1', 'A2', 'A3'})   # "1 failed, 1 passed" fails all
        self.assertEqual(report.tests_executed, 2)

    def test_a_passing_per_criterion_manifest_passes_every_covered_criterion(self):
        fixed = repo([
            {'name': 'A1 adds', 'argv': ['python', '-m', 'pytest', '-q', 'tests/test_app.py::test_a1_add'], 'acceptance_ids': ['A1']},
            {'name': 'A2 subtracts', 'argv': ['python', '-m', 'pytest', '-q', 'tests/test_app.py::test_a2_sub'], 'acceptance_ids': ['A2']},
            {'name': 'A3 documented', 'argv': ['python', '-m', 'pytest', '-q', 'tests/test_app.py::test_a1_add'], 'acceptance_ids': ['A3']},
        ])
        fixed['app.py'] = APP.replace('a - b + 1', 'a - b')
        report, _ = execute(fixed)
        self.assertTrue(report.passed, [f.__dict__ for f in report.failures])
        self.assertEqual(report.tests_executed, 3)


if __name__ == '__main__':
    unittest.main()
