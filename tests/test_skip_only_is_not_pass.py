"""Audit 2026-11-02 findings 2 + 14 (one family): a test run where every test is SKIPPED exits 0 and became PASS.

  finding 2  sandbox_executor.py / remote_sandbox.py judged a verify command by its exit code only.
  finding 14 release_policy.tests_status() inferred PASS from a passed chain.
Now: both executors read the runner's own summary (executed_tests); exit 0 with zero executed tests fails the criteria
with "no test executed", under the same taxonomy prefix. The report carries tests_executed, and the release check is
PASS only when it is > 0; 0 is NO_CHECKS (its own status, never PASS); unknown is UNKNOWN.
Seams: the local runner and the remote urlopen are replaced; the premise (a skip-only suite exits 0) is checked
against a real unittest run here and a real pytest run where pytest is installed (CI).
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

from omni_prod.autonomous_core import ExecutionReport
from omni_prod.failure_taxonomy import failure_type
from omni_prod.product_spec import AcceptanceCriterion, ProductSpec, Requirement
from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor
from omni_prod.sandbox import SandboxLimits
from omni_prod.sandbox_executor import NO_TEST_EXECUTED_MESSAGE, SandboxRepositoryExecutor, executed_tests

PYTEST = ['python', '-m', 'pytest', '-q']
ONE_SKIPPED = '\ns\n1 skipped in 0.01s\n'                         # pytest -q, a suite of one skipped test
TWO_PASSED_ONE_SKIPPED = '\n..s\n2 passed, 1 skipped in 0.02s\n'
SKIPPED_TEST = 'import pytest\n\n@pytest.mark.skip(reason="later")\ndef test_a1():\n    assert False\n'


def manifest(argv=PYTEST):
    return json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'], 'port': 8000,
                       'health_path': '/', 'build': [['python', '-m', 'compileall', '-q', '.']],
                       'verify': [{'name': 'unit tests', 'argv': argv, 'acceptance_ids': ['A1', 'A2']}]})


def repo(argv=PYTEST):
    return {'app.py': 'print("app")\n', 'tests/test_app.py': SKIPPED_TEST, '.omni/project.json': manifest(argv)}


def spec():
    return ProductSpec('scores', 'score keeper', 'web', (Requirement('R1', 'scores'),),
                       (AcceptanceCriterion('A1', 'R1', 'a score is saved'), AcceptanceCriterion('A2', 'R1', 'bad score 400')))


def local(stdout, rc=0, argv=PYTEST):
    def runner(*, command, **kw):
        return SimpleNamespace(returncode=rc if 'pytest' in command or 'unittest' in command else 0,
                               stdout=stdout if 'pytest' in command or 'unittest' in command else '', stderr='')
    return SandboxRepositoryExecutor(limits=SandboxLimits(), runner=runner).execute(repository=repo(argv), spec=spec())


def remote(stdout, rc=0):
    def urlopen(req, timeout):
        argv = json.loads(req.data)['argv']
        body = json.dumps({'returncode': rc if 'pytest' in argv else 0,
                           'stdout': stdout if 'pytest' in argv else '', 'stderr': ''}).encode()

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return Resp(body)
    ex = RemoteSandboxRepositoryExecutor(RemoteSandboxConfig('http://sandbox.invalid', 's' * 32), urlopen=urlopen)
    return ex.execute(repository=repo(), spec=spec())


class ReadingTheRunnerSummary(unittest.TestCase):
    def test_counts(self):
        cases = {
            ONE_SKIPPED: 0,
            TWO_PASSED_ONE_SKIPPED: 2,
            '\nF.\n1 failed, 1 passed in 0.03s\n': 2,
            '\nE\n1 error in 0.03s\n': 1,
            '\n========= 3 skipped, 1 deselected in 0.01s =========\n': 0,
            '\nx\n1 xfailed in 0.01s\n': 1,
            'garbage without a summary': None,
        }
        for out, expected in cases.items():
            with self.subTest(out=out.strip()[-40:]):
                self.assertEqual(executed_tests(PYTEST, out), expected)

    def test_unittest_and_unknown_runners(self):
        self.assertEqual(executed_tests(['python', '-m', 'unittest'], 'sss\nRan 3 tests in 0.001s\n\nOK (skipped=3)\n'), 0)
        self.assertEqual(executed_tests(['python', '-m', 'unittest'], '.s\nRan 2 tests in 0.001s\n\nOK (skipped=1)\n'), 1)
        self.assertIsNone(executed_tests(['npm', 'test'], '1 skipped in 0.01s'))     # unknown runner: unknown, not 0


class NegativeControlOneSkippedTestIsNotGreen(unittest.TestCase):
    def test_local_executor(self):
        report = local(ONE_SKIPPED)
        print('\n[local, 1 skipped]', report.passed, [(f.acceptance_id, f.message) for f in report.failures])
        self.assertFalse(report.passed)
        self.assertEqual({f.message for f in report.failures},
                         {f'verification failed: unit tests — {NO_TEST_EXECUTED_MESSAGE}'})
        self.assertEqual(sorted(f.acceptance_id for f in report.failures), ['A1', 'A2'])
        self.assertEqual(report.tests_executed, 0)

    def test_remote_executor(self):
        report = remote(ONE_SKIPPED)
        print('[remote, 1 skipped]', report.passed, [f.message for f in report.failures][:1])
        self.assertFalse(report.passed)
        self.assertEqual({f.message for f in report.failures},
                         {f'remote verification failed: unit tests — {NO_TEST_EXECUTED_MESSAGE}'})
        self.assertEqual(report.tests_executed, 0)

    def test_the_taxonomy_key_is_the_one_a_failing_test_gives(self):
        self.assertEqual(failure_type(f'verification failed: unit tests — {NO_TEST_EXECUTED_MESSAGE}'),
                         'verification_failed')
        self.assertEqual(failure_type(f'remote verification failed: unit tests — {NO_TEST_EXECUTED_MESSAGE}'),
                         'remote_verification_failed')

    def test_a_suite_where_tests_ran_still_passes_and_counts(self):
        for report in (local(TWO_PASSED_ONE_SKIPPED), remote(TWO_PASSED_ONE_SKIPPED)):
            self.assertTrue(report.passed)
            self.assertEqual(report.tests_executed, 2)


class ReleaseCheckNeedsAnExecutedTest(unittest.TestCase):
    def status(self, report, status='ready'):
        from omni_prod.release_policy import build_report
        result = SimpleNamespace(report=report, status=status, spec=None)
        ok = SimpleNamespace(passed=True, score=90, minimum_score=80, publish_allowed=True, status='CLEAR')
        q = build_report(build_id='b', artifact_sha256='0' * 64, result=result, evidence={}, quality=ok,
                         security=ok, rights=ok)
        return next(c for c in q.checks if c.check == 'sandbox_build_and_tests')

    def test_pass_only_with_executed_tests(self):
        from omni_prod.release_policy import NO_CHECKS, PASS, UNKNOWN
        self.assertEqual(self.status(ExecutionReport(True, tests_executed=3)).status, PASS)
        zero = self.status(ExecutionReport(True, tests_executed=0))
        self.assertEqual(zero.status, NO_CHECKS)
        self.assertTrue(zero.blocks)                                     # NO_CHECKS never releases
        self.assertEqual(self.status(ExecutionReport(True)).status, UNKNOWN)   # no count: not inferred from the chain


class Premise(unittest.TestCase):
    def write(self, d, name, text):
        os.makedirs(os.path.dirname(os.path.join(d, name)) or d, exist_ok=True)
        with open(os.path.join(d, name), 'w') as fh:
            fh.write(text)

    def test_real_unittest_skip_only_exits_0_and_reads_as_zero(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(d, 'test_x.py', 'import unittest\nclass T(unittest.TestCase):\n'
                                        '    @unittest.skip("later")\n    def test_a(self):\n        self.fail()\n')
            r = subprocess.run([sys.executable, '-m', 'unittest'], cwd=d, capture_output=True, text=True, timeout=60)
            print('\n[real unittest]', r.returncode, r.stderr.strip().splitlines()[-1:])
            self.assertEqual(r.returncode, 0)
            self.assertEqual(executed_tests(['python', '-m', 'unittest'], r.stdout + '\n' + r.stderr), 0)

    @unittest.skipUnless(importlib.util.find_spec('pytest'), 'pytest is not installed in this interpreter')
    def test_real_pytest_skip_only_exits_0_and_reads_as_zero(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(d, 'tests/test_app.py', SKIPPED_TEST)
            r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider'], cwd=d,
                               capture_output=True, text=True, timeout=120)
            print('\n[real pytest]', r.returncode, r.stdout.strip().splitlines()[-1:])
            self.assertEqual(r.returncode, 0)
            self.assertEqual(executed_tests(PYTEST, r.stdout), 0)


if __name__ == '__main__':
    unittest.main()
