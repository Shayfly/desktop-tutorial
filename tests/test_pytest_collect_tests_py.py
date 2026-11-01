"""bld_99ea49dfc6c843aabc90bb8cccbcc1d7 (founder 2026-11-02 00:59, decision a + c + b).

#205 let a root tests.py through the dependency gate, and the verify command `python -m pytest -q` collected nothing:
exit 5, "no tests ran", A1..A8 failed as "remote verification failed: unit tests" and three paid repairs chased test
logic that never ran.
  (a) the gate names it: tests.py (tests.py:N) is not collected by pytest; fix: rename / move it.
  (c) exit 5 from pytest gets its own message in BOTH executors, not "verification failed: <name>".
  (b) the generation constraints say where tests go and what they may import (no requests).
Seams: the local executor's runner and the remote executor's urlopen are replaced; everything else is real, and the
exit-5 premise itself is checked against a real pytest run.
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

from omni_prod import dependency_policy as dp
from omni_prod.failure_taxonomy import failure_type
from omni_prod.product_spec import AcceptanceCriterion, ProductSpec, Requirement
from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor
from omni_prod.sandbox import SandboxLimits
from omni_prod.sandbox_executor import NO_TESTS_COLLECTED_MESSAGE, SandboxRepositoryExecutor

PYTEST_VERIFY = [{'name': 'unit tests', 'argv': ['python', '-m', 'pytest', '-q'], 'acceptance_ids': ['A1', 'A2']}]
TESTS_PY = ('import threading, urllib.request\n'
            'import pytest\n'
            '\n'
            '@pytest.fixture\n'
            'def server():\n'
            '    yield None\n'
            '\n'
            'def test_flow(server):\n'
            '    assert True\n')
APP = 'import http.server\nprint("app")\n'


def manifest(verify=PYTEST_VERIFY):
    return json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'], 'port': 8000,
                       'health_path': '/', 'build': [['python', '-m', 'compileall', '-q', '.']], 'verify': verify})


def repo(**extra):
    r = {'app.py': APP, 'tests.py': TESTS_PY, '.omni/project.json': manifest()}
    r.update(extra)
    return {k: v for k, v in r.items() if v is not None}


def spec():
    return ProductSpec('scores', 'score keeper', 'web',
                       (Requirement('R1', 'scores'),),
                       (AcceptanceCriterion('A1', 'R1', 'a score is saved'), AcceptanceCriterion('A2', 'R1', 'bad score 400')))


class GateNamesTheUncollectedFile(unittest.TestCase):
    def test_the_bld_99ea49df_shape_is_blocked_with_file_line_and_fix(self):
        findings = dp.scan(repo())
        report = dp.unsupported_report(findings)
        message = report.failures[0].message
        print('\n[gate]', message)
        self.assertEqual(message, 'unsupported dependency: tests.py (tests.py:8): tests.py is not collected by pytest; '
                                  'fix: rename it to test_app.py or move it under tests/')
        self.assertEqual(report.failures[0].acceptance_id, 'UNSUPPORTED_DEPENDENCY')
        self.assertEqual(failure_type(message), 'unsupported_dependency')          # the taxonomy key does not change

    def test_the_sandbox_is_not_started(self):
        calls = []

        class Inner:
            def execute(self, *, repository, spec):
                calls.append(1)
        report = dp.DependencyGateExecutor(Inner()).execute(repository=repo(), spec=spec())
        self.assertFalse(report.passed)
        self.assertEqual(calls, [])

    def test_negative_controls_are_not_flagged(self):
        cases = {
            'tests/test_app.py beside it': repo(**{'tests/test_app.py': TESTS_PY}),
            'root test_app.py beside it': repo(**{'test_app.py': TESTS_PY}),
            'a *_test.py beside it': repo(**{'app_test.py': TESTS_PY}),
            'tests moved under tests/': repo(**{'tests.py': None, 'tests/test_app.py': TESTS_PY}),
            'no tests.py at all': repo(**{'tests.py': None}),
            'pytest is told the path': repo(**{'.omni/project.json': manifest([dict(PYTEST_VERIFY[0], argv=[
                'python', '-m', 'pytest', '-q', 'tests.py'])])}),
            'unittest discovers test*.py': repo(**{'.omni/project.json': manifest([dict(PYTEST_VERIFY[0], argv=[
                'python', '-m', 'unittest', 'discover'])])}),
            'pytest.ini sets python_files': repo(**{'pytest.ini': '[pytest]\npython_files = tests.py\n'}),
            'tests.py inside a package': {'app.py': APP, 'pkg/tests.py': TESTS_PY, '.omni/project.json': manifest()},
        }
        for name, r in cases.items():
            with self.subTest(name):
                self.assertFalse([f for f in dp.scan(r) if f.reason == dp.UNCOLLECTED_TESTS_REASON], name)

    def test_an_app_importing_pytest_is_still_blocked(self):
        # the #205 control: application code importing a test-only package is still a dependency failure
        message = dp.unsupported_report(dp.scan(repo(**{'app.py': 'import pytest\n'}))).failures[0].message
        self.assertIn('pytest (app.py:1): test-only package imported by application code', message)


class Exit5GetsItsOwnMessage(unittest.TestCase):
    def test_local_executor(self):
        for code, expected in ((5, NO_TESTS_COLLECTED_MESSAGE), (1, 'verification failed: unit tests')):
            def runner(*, command, **kw):
                ok = command[:2] != ['python', '-m'] or command[2] != 'pytest'
                return SimpleNamespace(returncode=0 if ok else code, stdout='\n\nno tests ran in 0.00s\n', stderr='')
            ex = SandboxRepositoryExecutor(limits=SandboxLimits(), runner=runner)
            r = repo(**{'tests.py': None, 'tests/test_app.py': TESTS_PY})
            report = ex.execute(repository=r, spec=spec())
            with self.subTest(code=code):
                self.assertEqual({f.message for f in report.failures}, {expected})
                self.assertFalse(report.passed)

    def test_remote_executor_real_run_only_http_faked(self):
        for code, expected in ((5, NO_TESTS_COLLECTED_MESSAGE), (1, 'remote verification failed: unit tests')):
            def urlopen(req, timeout):
                argv = json.loads(req.data)['argv']
                rc = code if 'pytest' in argv else 0
                body = json.dumps({'returncode': rc, 'stdout': '\n\n\nno tests ran in 0.00s\n\n', 'stderr': ''}).encode()

                class Resp(io.BytesIO):
                    def __enter__(self):
                        return self

                    def __exit__(self, *a):
                        return False
                return Resp(body)
            ex = RemoteSandboxRepositoryExecutor(RemoteSandboxConfig('http://sandbox.invalid', 's' * 32), urlopen=urlopen)
            report = ex.execute(repository=repo(**{'tests.py': None, 'tests/test_app.py': TESTS_PY}), spec=spec())
            print(f'\n[remote exit {code}]', [(f.acceptance_id, f.message) for f in report.failures])
            with self.subTest(code=code):
                self.assertEqual({f.message for f in report.failures}, {expected})
                self.assertEqual(sorted(f.acceptance_id for f in report.failures), ['A1', 'A2'])
                self.assertFalse(report.passed)                                       # exit 5 never passes

    def test_exit5_from_a_non_pytest_command_keeps_the_old_message(self):
        from omni_prod.sandbox_executor import verify_failure_message
        self.assertEqual(verify_failure_message('unit tests', ['python', '-m', 'unittest'], 5), 'verification failed: unit tests')

    @unittest.skipUnless(importlib.util.find_spec('pytest'), 'pytest is not installed in this interpreter')
    def test_the_premise_real_pytest_exits_5_on_a_root_tests_py(self):
        with tempfile.TemporaryDirectory() as d:
            for name, text in (('app.py', APP), ('tests.py', TESTS_PY)):
                with open(os.path.join(d, name), 'w') as fh:
                    fh.write(text)
            r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider'], cwd=d,
                               capture_output=True, text=True, timeout=120)
            print('\n[real pytest]', r.returncode, r.stdout.strip().splitlines()[-1:])
            self.assertEqual(r.returncode, 5)
            self.assertIn('no tests ran', r.stdout)


class GenerationConstraints(unittest.TestCase):
    def test_tests_location_and_imports_are_stated(self):
        c = dp.GENERATION_CONSTRAINTS
        self.assertIn('Tests go in tests/test_<topic>.py', c)
        self.assertIn('never in a file named tests.py at the repository root', c)
        self.assertIn('Tests import only the Python standard library and pytest -- never requests', c)


if __name__ == '__main__':
    unittest.main()
