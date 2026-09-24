"""M2 Revision 4 (native adaptation) unit tests.

Exercises the REAL SandboxRepositoryExecutor / apply_patch with their actual,
unchanged public signatures -- no mocked-out class, no reimplementation.
Docker integration is intentionally not exercised here (registry-1.docker.io
is blocked in this sandbox; see PATCH_APPLICATION_REPORT.md), so the sandbox
executor is exercised the same way tests/test_v22_sandbox_executor.py already
does: a fake `runner` callable stands in for the docker invocation, so what's
under test is the executor's own decision logic, not docker itself.
"""
import json
import unittest

from omni_prod.product_spec import ProductSpec
from omni_prod.sandbox import SandboxLimits, SandboxResult
from omni_prod.sandbox_executor import SandboxRepositoryExecutor
from omni_prod.repository_patch import FilePatch, PatchValidationError, apply_patch, parse_patch

SPEC = ProductSpec.from_dict({
    'title': 'X', 'summary': 'X app', 'stack': ['python'],
    'requirements': [{'id': 'R1', 'text': 'works', 'kind': 'functional', 'mandatory': True}],
    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'tests pass'}],
})


class Runner:
    """Same fixture shape as tests/test_v22_sandbox_executor.py's Runner."""
    def __init__(self, codes):
        self.codes = list(codes)
        self.commands = []

    def __call__(self, **kwargs):
        self.commands.append(kwargs['command'])
        code = self.codes.pop(0)
        return SandboxResult(code, 'ok' if code == 0 else '', 'boom' if code else '')


def repo_with_verify(verify_entry):
    return {
        'app.py': 'print("ok")',
        '.omni/project.json': json.dumps({
            'build': [['python', '-m', 'compileall', '-q', '.']],
            'verify': [verify_entry],
        }),
    }


class FakeVerificationRejectedTests(unittest.TestCase):
    def test_verify_true_is_rejected_without_running_the_sandbox(self):
        repo = repo_with_verify({'name': 'acceptance', 'argv': ['true'], 'acceptance_ids': ['A1']})
        # One code queued for the build-phase command only. The fake verify
        # check must be caught before the verify phase ever calls the
        # runner -- if it isn't, popping from this exhausted list raises
        # IndexError and fails the test loudly (this caught a real bug in
        # the first version of this test: the build command runs first and
        # also consumes a runner call).
        runner = Runner([0])
        result = SandboxRepositoryExecutor(limits=SandboxLimits(), runner=runner).execute(
            repository=repo, spec=SPEC,
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.failures[0].acceptance_id, 'A1')
        self.assertIn('Fake verification command detected', result.failures[0].evidence)
        self.assertEqual(
            runner.commands, [['python', '-m', 'compileall', '-q', '.']],
            'only the build command may reach the sandbox; the fake verify check must not',
        )

    def test_echo_verify_is_rejected(self):
        repo = repo_with_verify({'name': 'acceptance', 'argv': ['echo', 'ok'], 'acceptance_ids': ['A1']})
        runner = Runner([0])
        result = SandboxRepositoryExecutor(limits=SandboxLimits(), runner=runner).execute(
            repository=repo, spec=SPEC,
        )
        self.assertFalse(result.passed)
        self.assertEqual(runner.commands, [['python', '-m', 'compileall', '-q', '.']])

    def test_real_verification_command_still_runs_and_can_pass(self):
        repo = repo_with_verify({'name': 'acceptance', 'argv': ['pytest', '-q'], 'acceptance_ids': ['A1']})
        runner = Runner([0, 0])  # build command + real verify command
        result = SandboxRepositoryExecutor(limits=SandboxLimits(), runner=runner).execute(
            repository=repo, spec=SPEC,
        )
        self.assertTrue(result.passed)
        self.assertEqual(len(runner.commands), 2)


class PathTraversalRejectedTests(unittest.TestCase):
    def test_parse_patch_rejects_traversal(self):
        with self.assertRaises(PatchValidationError):
            parse_patch({'files': [{'path': '../secret.py', 'content': 'x'}]})

    def test_apply_patch_rejects_traversal_even_when_parse_patch_is_bypassed(self):
        # Constructs FilePatch directly, the same way omni_prod/v27_platform.py
        # does, instead of going through parse_patch() -- this is exactly the
        # path that was unguarded before this change.
        bad_patch = (FilePatch(path='../../etc/passwd', content='pwned'),)
        with self.assertRaises(ValueError):
            apply_patch({'a.py': '1'}, bad_patch)

    def test_apply_patch_rejects_absolute_path(self):
        with self.assertRaises(ValueError):
            apply_patch({}, (FilePatch(path='/etc/passwd', content='pwned'),))

    def test_apply_patch_still_works_for_normal_paths(self):
        result = apply_patch({'a.py': '1'}, (FilePatch(path='b.py', content='2'),))
        self.assertEqual(result, {'a.py': '1', 'b.py': '2'})


if __name__ == '__main__':
    unittest.main()
