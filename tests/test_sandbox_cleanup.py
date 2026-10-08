"""Sandbox containers never block later builds (library rehearsal 2026-10-09:
"Conflict. The container name /omni-build-t2 is already in use")."""
import subprocess
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from omni_prod import sandbox
from omni_prod.sandbox import SandboxLimits, build_docker_command, container_name, sweep_stale_containers


class NamingTests(unittest.TestCase):
    def test_names_are_unique_and_labelled(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            a = build_docker_command(source_dir=d, build_id='t2', limits=SandboxLimits(), command=['true'])
            b = build_docker_command(source_dir=d, build_id='t2', limits=SandboxLimits(), command=['true'])
        na, nb = a[a.index('--name') + 1], b[b.index('--name') + 1]
        self.assertNotEqual(na, nb)
        self.assertTrue(na.startswith('omni-build-t2-'))
        self.assertIn('omni.sandbox=1', a)
        self.assertRegex(container_name('preview-smoke'), r'^omni-build-preview-smoke-[0-9a-f]{10}$')


class SweepTests(unittest.TestCase):
    def test_only_old_sandbox_containers_are_removed(self):
        calls = []

        def runner(argv, **kw):
            calls.append(argv)
            if argv[:2] == ['docker', 'ps']:
                return SimpleNamespace(stdout='\n'.join([
                    'aaa|omni-build-t2|2026-10-09 01:00:00 +0000 UTC',          # hung, old: removed
                    'bbb|omni-build-t1-1a2b3c4d5e|2026-10-09 01:59:30 +0000 UTC',  # running now: kept
                    'ccc|some-other|2026-10-08 01:00:00 +0000 UTC',              # not ours: kept
                ]))
            return SimpleNamespace(stdout='')
        removed = sweep_stale_containers(300, runner=runner, now=datetime(2026, 10, 9, 2, 0, tzinfo=timezone.utc))
        self.assertEqual(removed, ['omni-build-t2'])
        self.assertIn(['docker', 'rm', '-f', 'aaa'], calls)
        self.assertNotIn(['docker', 'rm', '-f', 'bbb'], calls)

    def test_docker_errors_never_fail_the_caller(self):
        def boom(*a, **k):
            raise OSError('no docker')
        self.assertEqual(sweep_stale_containers(10, runner=boom), [])


class TimeoutTests(unittest.TestCase):
    def test_timeout_removes_the_container_and_reports_failure(self):
        import tempfile
        seen = []

        def fake_run(argv, **kw):
            seen.append(argv)
            if argv[:2] == ['docker', 'run']:
                raise subprocess.TimeoutExpired(argv, kw.get('timeout'), output=b'partial', stderr=b'')
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        with tempfile.TemporaryDirectory() as d, mock.patch.object(sandbox.subprocess, 'run', side_effect=fake_run):
            result = sandbox.run_sandbox(source_dir=d, build_id='t2', limits=SandboxLimits(timeout_seconds=5), command=['sleep', '99'])
        self.assertEqual(result.returncode, 124)
        self.assertIn('timed out after 5s', result.stderr)
        run_argv = next(a for a in seen if a[:2] == ['docker', 'run'])
        name = run_argv[run_argv.index('--name') + 1]
        self.assertIn(['docker', 'rm', '-f', name], seen)


if __name__ == '__main__':
    unittest.main()
