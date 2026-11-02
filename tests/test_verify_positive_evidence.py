"""Audit 2026-11-02 finding 3: `python -c "import app"` counted as a test.

The fake-verification detector was a NEGATIVE list (echo, true, `python -c` without the word "import"...). It is now
a POSITIVE requirement (sandbox_executor.verification_evidence_problem): a verify command is evidence only when it runs
python -m pytest / pytest / python -m unittest, and not in a mode that runs no test (--collect-only, --help, ...).
Anything else fails its criteria before the sandbox is called, in both executors.

Strict request mode (OMNI_SANDBOX_STRICT_REQUEST_V1) stays OFF by default -- decision recorded here as a test: the
browser probe and visual QA call the same /run endpoint with profile='browser' and a staged script that is not in the
manifest, and strict mode rejects both, so turning it on by default would fail every build at the browser stage.
"""
import io
import json
import unittest
from types import SimpleNamespace

from omni_prod.product_spec import AcceptanceCriterion, ProductSpec, Requirement
from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor
from omni_prod.sandbox import SandboxLimits
from omni_prod.sandbox_executor import SandboxRepositoryExecutor, verification_evidence_problem
from omni_prod.sandbox_request_policy import SandboxRequestRejected, validate_command

IMPORT_APP = ['python', '-c', 'import app']                  # the finding, verbatim


def manifest(argv):
    return json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'], 'port': 8000,
                       'health_path': '/', 'build': [['python', '-m', 'compileall', '-q', '.']],
                       'verify': [{'name': 'smoke', 'argv': argv, 'acceptance_ids': ['A1']}]})


def repo(argv):
    return {'app.py': 'print("app")\n', '.omni/project.json': manifest(argv)}


def spec():
    return ProductSpec('scores', 'score keeper', 'web', (Requirement('R1', 'scores'),),
                       (AcceptanceCriterion('A1', 'R1', 'a score is saved'),))


class PositiveRequirement(unittest.TestCase):
    def test_only_recognised_runners_are_evidence(self):
        not_evidence = [IMPORT_APP, ['python', '-c', 'import app; assert app.ok()'], ['python3', '-c', 'import pytest'],
                        ['python', 'app.py'], ['python', 'tests/test_app.py'], ['node', 'test.js'], ['npm', 'test'],
                        ['sh', '-c', 'python -m pytest'], ['echo', 'ok'], ['true'], [],
                        ['python', '-m', 'pytest', '--collect-only'], ['python', '-m', 'pytest', '--co', '-q'],
                        ['pytest', '--help'], ['python', '-m', 'http.server']]
        evidence = [['python', '-m', 'pytest', '-q'], ['python3', '-m', 'pytest', '-q', 'tests/test_app.py::test_a1'],
                    ['python3.12', '-m', 'pytest'], ['pytest', 'tests/'], ['/usr/bin/python3', '-m', 'unittest', '-v']]
        for argv in not_evidence:
            with self.subTest(argv=argv):
                self.assertIsNotNone(verification_evidence_problem(argv))
        for argv in evidence:
            with self.subTest(argv=argv):
                self.assertIsNone(verification_evidence_problem(argv))


class NegativeControlImportAppIsNotATest(unittest.TestCase):
    def test_local_executor_fails_it_without_running_it(self):
        calls = []

        def runner(*, command, **kw):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        report = SandboxRepositoryExecutor(limits=SandboxLimits(), runner=runner).execute(repository=repo(IMPORT_APP), spec=spec())
        print('\n[local, python -c "import app"]', report.passed, [(f.acceptance_id, f.evidence[:90]) for f in report.failures])
        self.assertFalse(report.passed)
        self.assertEqual([f.acceptance_id for f in report.failures], ['A1'])
        self.assertIn('not a test runner', report.failures[0].evidence)
        self.assertNotIn(IMPORT_APP, calls)                    # never sent to the sandbox

    def test_remote_executor_fails_it_without_running_it(self):
        sent = []

        def urlopen(req, timeout):
            sent.append(json.loads(req.data)['argv'])
            body = json.dumps({'returncode': 0, 'stdout': '', 'stderr': ''}).encode()

            class Resp(io.BytesIO):
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False
            return Resp(body)
        ex = RemoteSandboxRepositoryExecutor(RemoteSandboxConfig('http://sandbox.invalid', 's' * 32), urlopen=urlopen)
        report = ex.execute(repository=repo(IMPORT_APP), spec=spec())
        print('[remote, python -c "import app"]', report.passed, [f.message for f in report.failures])
        self.assertFalse(report.passed)
        self.assertEqual([f.message for f in report.failures], ['verification failed: smoke'])   # taxonomy unchanged
        self.assertNotIn(IMPORT_APP, sent)

    def test_a_real_pytest_command_still_reaches_the_sandbox(self):
        calls = []

        def runner(*, command, **kw):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout='1 passed in 0.01s\n', stderr='')
        argv = ['python', '-m', 'pytest', '-q', 'tests/test_app.py::test_a1']
        report = SandboxRepositoryExecutor(limits=SandboxLimits(), runner=runner).execute(repository=repo(argv), spec=spec())
        self.assertTrue(report.passed)
        self.assertIn(argv, calls)


class StrictModeStaysOffByDefault(unittest.TestCase):
    def test_strict_would_reject_the_browser_probe_and_a_staged_probe_script(self):
        r = repo(['python', '-m', 'pytest', '-q'])
        with self.assertRaises(SandboxRequestRejected):                     # browser probe / visual QA profile
            validate_command(['python', '.omni_probe/browser_probe.py'], build_id='bld-browser-probe', strict=True,
                             repository=r, profile='browser')
        with self.assertRaises(SandboxRequestRejected):                     # a staged script not in the manifest
            validate_command(['python', '.omni_probe/behavior.py'], build_id='bld-behavior', strict=True,
                             repository=r, profile='default')
        validate_command(['python', '.omni_probe/browser_probe.py'], build_id='bld-browser-probe', strict=False,
                         repository=r, profile='browser')                   # today's default accepts it


if __name__ == '__main__':
    unittest.main()
