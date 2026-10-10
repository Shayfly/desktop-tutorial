from __future__ import annotations

"""Real unit tests for M3 Revision 2 (preview runtime) and the M1 blocker fixes.

What is real here: every decision the code makes -- preview contract parsing,
the exact `docker run` argv, host-port parsing, external URL construction,
durable-workspace enforcement, the health-probe loop, the launch/stop state
machine, the build worker's gate ordering and settle-vs-release billing, the
outbox relay, the SQL each repository method emits, and the model-spend
ledger (produced by the real `model_policy.authorize_model_call`).

What is faked, and why: `subprocess.run` (no Docker registry in this sandbox),
the Postgres pool (no psycopg here -- the fake mirrors DatabasePool's
context-manager contract from omni_prod/db.py), and the heavy collaborators
of the build worker (AI engine, rights engine, branding). The RQ entrypoints
themselves (`execute_live_build_job`, `execute_preview_launch`,
`stop_preview_task`) and the FastAPI routes import `investor_app`, which needs
`fastapi` (not installable here); their logic lives in the dependency-injected
`_run_*` functions tested below, and the wrappers only wire real dependencies.

Run with: python3 -m unittest tests.test_m3_preview_logic -v
"""

import json
import os
import stat
import subprocess
import tempfile
import unittest
from tests.policy_fixtures import ACCEPTED_SPEC, verified_chain
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from omni_prod import worker_tasks
from omni_prod.autonomous_agents import _GENERATOR_SYSTEM
from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.job_repository import PostgresBuildRepository
from omni_prod.model_gateway import ModelEndpoint
from omni_prod.model_policy import ModelUsePolicy, ModelUseState, authorize_model_call
from omni_prod.models import BuildStatus
from omni_prod.preview_repository import PostgresPreviewRepository
from omni_prod.preview_runtime import (
    DEFAULT_ALLOWED_RUNTIMES, SECURITY_FLAGS, DockerPreviewProvider, NotPreviewable,
    PreviewBackendUnavailable, PreviewContract, StartedPreview, build_run_argv,
    ensure_durable_workspace, external_preview_url, is_managed_workdir, parse_docker_port_output,
    parse_preview_contract, wait_until_healthy, _materialize_repository,
)
from omni_prod.project_manifest import ProjectManifest
from omni_prod.queueing import BUILD_QUEUE, enqueue_build, preview_host_queue
from omni_prod.repository_patch import PatchValidationError
from omni_prod.rights_ip import GateStatus, RightKind, RightsEvidence
from omni_prod.workspace import MemoryProjectWorkspace, PostgresProjectWorkspace, ProjectWorkspace

TEMPLATE = 'https://{preview_id}.preview.148ai.com'


def manifest(**overrides) -> dict:
    data = {
        'schema_version': 2, 'runtime': 'python:3.11-slim',
        'start': ['python', '-m', 'http.server', '3000'], 'port': 3000, 'health_path': '/',
        'build': [['python', '-m', 'compileall', '-q', '.']],
        'verify': [{'name': 'unit', 'argv': ['python', '-m', 'unittest'], 'acceptance_ids': ['AC-1']}],
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not _DROP}


_DROP = object()


def repo_with(**overrides) -> dict[str, str]:
    return {'.omni/project.json': json.dumps(manifest(**overrides)), 'index.html': '<h1>hi</h1>'}


def contract(**kw) -> PreviewContract:
    base = dict(runtime='python:3.11-slim', start=('python', '-m', 'http.server', '3000'), port=3000, health_path='/')
    base.update(kw)
    return PreviewContract(**base)


# ===========================================================================
# STEP 2 -- versioned preview contract
# ===========================================================================

class TestPreviewContract(unittest.TestCase):
    def test_valid_schema_v2_contract(self):
        c = parse_preview_contract(repo_with(), allowed=DEFAULT_ALLOWED_RUNTIMES)
        self.assertEqual(c, contract())

    def test_node_runtime_allowed(self):
        c = parse_preview_contract(repo_with(runtime='node:20-slim', start=['npm', 'start']),
                                   allowed=DEFAULT_ALLOWED_RUNTIMES)
        self.assertEqual((c.runtime, c.start), ('node:20-slim', ('npm', 'start')))

    def test_health_path_defaults_to_root(self):
        self.assertEqual(parse_preview_contract(repo_with(health_path=_DROP)).health_path, '/')

    def test_contract_coexists_with_build_verify_manifest(self):
        # The same file still parses through the untouched ProjectManifest
        # used by the build sandbox, quality gate and security scan.
        repo = repo_with()
        m = ProjectManifest.from_repository(repo)
        self.assertEqual(m.verify[0].acceptance_ids, ('AC-1',))
        self.assertEqual(parse_preview_contract(repo).port, 3000)

    def _rejects(self, repo, fragment):
        with self.assertRaises(NotPreviewable) as ctx:
            parse_preview_contract(repo, allowed=DEFAULT_ALLOWED_RUNTIMES)
        self.assertIn(fragment, str(ctx.exception))

    def test_missing_manifest(self):
        self._rejects({'index.html': 'x'}, 'no .omni/project.json')

    def test_invalid_json(self):
        self._rejects({'.omni/project.json': '{nope'}, 'invalid')

    def test_legacy_manifest_without_schema_version(self):
        self._rejects(repo_with(schema_version=_DROP), 'schema_version 2')

    def test_schema_version_1_string_and_bool_rejected(self):
        for bad in (1, '2', True, 2.0):
            with self.subTest(bad=bad):
                self._rejects(repo_with(schema_version=bad), 'schema_version 2')

    def test_runtime_outside_allowlist_rejected(self):
        # Untrusted manifest must never pick an arbitrary image.
        for bad in ('attacker/miner:latest', 'python:3.11', 'ubuntu', None, 3):
            with self.subTest(bad=bad):
                self._rejects(repo_with(runtime=bad), 'not an allowed preview runtime')

    def test_runtime_allowlist_env_override(self):
        with patch.dict(os.environ, {'OMNI_PREVIEW_ALLOWED_RUNTIMES': 'registry.internal/py:1, node:20-slim'}):
            self.assertEqual(parse_preview_contract(repo_with(runtime='registry.internal/py:1')).runtime,
                             'registry.internal/py:1')
            with self.assertRaises(NotPreviewable):
                parse_preview_contract(repo_with(runtime='python:3.11-slim'))

    def test_bad_start(self):
        for bad in (None, [], 'python app.py', ['python', 1], ['python', ''], ['a\x00b']):
            with self.subTest(bad=bad):
                self._rejects(repo_with(start=bad), 'start')

    def test_bad_port(self):
        for bad in (None, 0, 70000, '3000', True, 3000.0):
            with self.subTest(bad=bad):
                self._rejects(repo_with(port=bad), 'port')

    def test_bad_health_path(self):
        for bad in ('health', '//evil.example/x', '/../etc', '/a b', 'http://x/', 7):
            with self.subTest(bad=bad):
                self._rejects(repo_with(health_path=bad), 'health_path')

    def test_generator_prompt_emits_the_contract(self):
        for token in ('"schema_version": 2', 'python:3.11-slim', 'node:20-slim', '"start"', '"port"',
                      '"health_path"', '0.0.0.0',
                      # Decision change 2026-10-07: every product is a website, the
                      # preview keys are required and checked by a real start in the
                      # sandbox (preview_smoke) instead of being optional.
                      'preview keys are required'):
            self.assertIn(token, _GENERATOR_SYSTEM)


# ===========================================================================
# STEP 3 -- docker run argv, dynamic ports, provider
# ===========================================================================

class TestRunArgv(unittest.TestCase):
    def setUp(self):
        self.c = contract(start=('npm', 'start'), runtime='node:20-slim')
        self.argv = build_run_argv(preview_id='prv_abc', contract=self.c, workdir='/tmp/omni-preview-prv_abc-x')

    def test_security_flags_come_first_in_exact_order(self):
        self.assertEqual(self.argv[:2], ['docker', 'run'])
        self.assertEqual(tuple(self.argv[2:2 + len(SECURITY_FLAGS)]), SECURITY_FLAGS)
        for flag in ('--cpus=0.5', '--memory=512m', '--pids-limit=64', '--read-only',
                     '--cap-drop=ALL', '--security-opt=no-new-privileges'):
            self.assertIn(flag, SECURITY_FLAGS)
        i = self.argv.index('--tmpfs')
        self.assertTrue(self.argv[i + 1].startswith('/tmp:'))

    def test_image_then_start_command_are_last(self):
        n = len(self.c.start)
        self.assertEqual(self.argv[-n:], ['npm', 'start'])
        self.assertEqual(self.argv[-n - 1], 'node:20-slim')
        # every docker option precedes the image; nothing after it but the command
        image_at = len(self.argv) - n - 1
        self.assertFalse(any(t.startswith('-') for t in self.argv[image_at + 1:]))
        self.assertLess(self.argv.index('-d'), image_at)
        self.assertLess(self.argv.index('--mount'), image_at)

    def test_docker_allocates_host_port_on_one_interface(self):
        self.assertNotIn('-P', self.argv)  # see build_run_argv docstring
        i = self.argv.index('-p')
        self.assertEqual(self.argv[i + 1], '127.0.0.1::3000')  # empty host port = Docker picks
        custom = build_run_argv(preview_id='p', contract=self.c, workdir='/w', bind_address='10.0.0.5')
        self.assertIn('10.0.0.5::3000', custom)

    def test_readonly_source_mount_nonroot_and_no_escape_hatches(self):
        mount = self.argv[self.argv.index('--mount') + 1]
        self.assertEqual(mount, 'type=bind,src=/tmp/omni-preview-prv_abc-x,dst=/workspace,readonly')
        self.assertIn('65534:65534', self.argv)
        self.assertIn('PORT=3000', self.argv)
        for forbidden in ('--privileged', '--rm', '--network=host', '--pid=host'):
            self.assertNotIn(forbidden, self.argv)

    def test_unsafe_preview_id_rejected(self):
        with self.assertRaises(ValueError):
            build_run_argv(preview_id='x/../y', contract=self.c, workdir='/w')


class TestDockerPortParsing(unittest.TestCase):
    def test_single_binding(self):
        self.assertEqual(parse_docker_port_output('127.0.0.1:49153\n'), 49153)

    def test_ipv4_and_ipv6_bindings(self):
        self.assertEqual(parse_docker_port_output('0.0.0.0:32768\n[::]:32768\n'), 32768)

    def test_garbage(self):
        for bad in ('', 'Error: No public port', 'host:notaport'):
            with self.subTest(bad=bad), self.assertRaises(RuntimeError):
                parse_docker_port_output(bad)


class ScriptedRunner:
    """Stands in for subprocess.run: records argv, returns queued results."""

    def __init__(self, results):
        self.results = list(results)
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        rc, out, err = self.results.pop(0)
        return subprocess.CompletedProcess(argv, rc, out, err)


def _preview_dirs() -> set[str]:
    tmp = tempfile.gettempdir()
    return {n for n in os.listdir(tmp) if n.startswith('omni-preview-')}


class TestDockerPreviewProviderStart(unittest.TestCase):
    def test_success_runs_then_asks_docker_for_the_port(self):
        runner = ScriptedRunner([(0, 'cid123\n', ''), (0, '127.0.0.1:49999\n', '')])
        provider = DockerPreviewProvider(workspace=None, runner=runner, bind_address='127.0.0.1')
        started = provider.start(preview_id='prv_ok', project_id='p', version_id='v', repository=repo_with())
        try:
            self.assertEqual((started.container_id, started.host_port), ('cid123', 49999))
            self.assertEqual(runner.calls[0][:2], ['docker', 'run'])
            self.assertEqual(runner.calls[1], ['docker', 'port', 'cid123', '3000/tcp'])
            root = Path(started.workdir)
            self.assertTrue(is_managed_workdir(started.workdir))
            self.assertEqual((root / 'index.html').read_text(), '<h1>hi</h1>')
            # uid 65534 with no CAP_DAC_OVERRIDE must be able to read it
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((root / '.omni').stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((root / 'index.html').stat().st_mode), 0o644)
        finally:
            provider.remove_workdir(started.workdir)
        self.assertFalse(Path(started.workdir).exists())

    def test_docker_run_failure_removes_workdir(self):
        before = _preview_dirs()
        runner = ScriptedRunner([(125, '', 'Unable to find image')])
        provider = DockerPreviewProvider(workspace=None, runner=runner)
        with self.assertRaises(RuntimeError) as ctx:
            provider.start(preview_id='prv_fail', project_id='p', version_id='v', repository=repo_with())
        self.assertIn('Unable to find image', str(ctx.exception))
        self.assertEqual(_preview_dirs(), before)

    def test_docker_port_failure_on_running_container_removes_container_and_workdir(self):
        before = _preview_dirs()
        runner = ScriptedRunner([(0, 'cid9\n', ''), (1, '', 'no public port'), (0, 'true 0\n', ''), (0, 'cid9\n', '')])
        provider = DockerPreviewProvider(workspace=None, runner=runner)
        with self.assertRaises(RuntimeError):
            provider.start(preview_id='prv_port', project_id='p', version_id='v', repository=repo_with())
        self.assertEqual(runner.calls[2][:2], ['docker', 'inspect'])
        self.assertEqual(runner.calls[3], ['docker', 'rm', '-f', 'cid9'])
        self.assertEqual(_preview_dirs(), before)

    def test_crash_on_boot_is_handed_back_for_diagnosis_not_destroyed(self):
        # Regression pinned by the live Docker test: an app that exits at once
        # has no published port; the container (and its logs) must survive
        # start() so the worker can report the exit code and log tail.
        runner = ScriptedRunner([(0, 'cid7\n', ''), (1, '', "no public port '3000/tcp' published"), (0, 'false 3\n', '')])
        provider = DockerPreviewProvider(workspace=None, runner=runner)
        started = provider.start(preview_id='prv_crash', project_id='p', version_id='v', repository=repo_with())
        try:
            self.assertEqual((started.container_id, started.host_port), ('cid7', None))
            self.assertNotIn(['docker', 'rm', '-f', 'cid7'], runner.calls)
            self.assertTrue(Path(started.workdir).exists())
        finally:
            provider.remove_workdir(started.workdir)

    def test_tmpfs_is_writable_by_the_nonroot_user(self):
        # Regression pinned by the live Docker test: without mode=1777 uid
        # 65534 gets PermissionError on /tmp.
        tmpfs = SECURITY_FLAGS[SECURITY_FLAGS.index('--tmpfs') + 1]
        self.assertIn('mode=1777', tmpfs.split(':', 1)[1].split(','))

    def test_not_previewable_has_no_side_effects(self):
        before = _preview_dirs()
        runner = ScriptedRunner([])
        provider = DockerPreviewProvider(workspace=None, runner=runner)
        with self.assertRaises(NotPreviewable):
            provider.start(preview_id='prv_np', project_id='p', version_id='v', repository=repo_with(schema_version=_DROP))
        self.assertEqual(runner.calls, [])
        self.assertEqual(_preview_dirs(), before)

    def test_unsafe_preview_id_has_no_side_effects(self):
        before = _preview_dirs()
        runner = ScriptedRunner([])
        with self.assertRaises(ValueError):
            DockerPreviewProvider(workspace=None, runner=runner).start(
                preview_id='bad/id', project_id='p', version_id='v', repository=repo_with())
        self.assertEqual((runner.calls, _preview_dirs()), ([], before))

    def test_loads_repository_from_workspace_when_not_given(self):
        ws = MagicMock()
        ws.get.return_value.repository.return_value = repo_with()
        runner = ScriptedRunner([(0, 'cid\n', ''), (0, '127.0.0.1:40000\n', '')])
        provider = DockerPreviewProvider(workspace=ws, runner=runner)
        started = provider.start(preview_id='prv_ws', project_id='proj', version_id='ver')
        provider.remove_workdir(started.workdir)
        ws.get.assert_called_once_with(project_id='proj', version_id='ver')


class TestDockerPreviewProviderOps(unittest.TestCase):
    def test_stop_is_idempotent_for_missing_container(self):
        runner = ScriptedRunner([(1, '', 'Error: No such container: cid')])
        DockerPreviewProvider(workspace=None, runner=runner).stop('cid')
        self.assertEqual(runner.calls, [['docker', 'rm', '-f', 'cid']])

    def test_stop_raises_on_real_failure(self):
        runner = ScriptedRunner([(1, '', 'Cannot connect to the Docker daemon')])
        with self.assertRaises(RuntimeError):
            DockerPreviewProvider(workspace=None, runner=runner).stop('cid')

    def test_is_running_parsing(self):
        p = DockerPreviewProvider(workspace=None, runner=ScriptedRunner([
            (0, 'true 0\n', ''), (0, 'false 137\n', ''), (1, '', 'No such object')]))
        self.assertEqual(p.is_running('c'), (True, 0))
        self.assertEqual(p.is_running('c'), (False, 137))
        self.assertEqual(p.is_running('c'), (False, None))

    def test_logs(self):
        p = DockerPreviewProvider(workspace=None, runner=ScriptedRunner([(0, 'out\n', 'err\n')]))
        self.assertEqual(p.logs('c', tail=5), 'out\nerr\n')

    def test_remove_workdir_refuses_paths_it_did_not_create(self):
        p = DockerPreviewProvider(workspace=None, runner=ScriptedRunner([]))
        with tempfile.TemporaryDirectory() as foreign:
            self.assertFalse(p.remove_workdir(foreign))
            self.assertTrue(Path(foreign).exists())
        for bad in (None, '', '/etc', '/', os.path.join(tempfile.gettempdir(), 'omni-preview-x', '..')):
            self.assertFalse(p.remove_workdir(bad))
        self.assertTrue(Path('/etc').exists())

    def test_materialize_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as td, self.assertRaises(PatchValidationError):
            _materialize_repository(Path(td), {'../evil.txt': 'x'})


# ===========================================================================
# STEP 4 -- health probe + external URL
# ===========================================================================

class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class TestHealthProbe(unittest.TestCase):
    def test_becomes_healthy_after_connection_refused(self):
        clock = FakeClock()
        answers = [ConnectionRefusedError('refused'), ConnectionRefusedError('refused'), 200]

        def http_get(url, timeout):
            a = answers.pop(0)
            if isinstance(a, Exception):
                raise a
            return a

        r = wait_until_healthy(url='http://127.0.0.1:1/', is_alive=lambda: (True, None), timeout_seconds=30,
                               interval_seconds=1, http_get=http_get, sleep=clock.sleep, clock=clock)
        self.assertTrue(r.ok)
        self.assertEqual(r.attempts, 3)

    def test_server_errors_and_404_are_not_healthy(self):
        clock = FakeClock()
        r = wait_until_healthy(url='u', is_alive=lambda: (True, None), timeout_seconds=5, interval_seconds=1,
                               http_get=lambda u, t: 404, sleep=clock.sleep, clock=clock)
        self.assertFalse(r.ok)
        self.assertIn('timed out', r.detail)
        self.assertIn('HTTP 404', r.detail)

    def test_exited_container_fails_immediately(self):
        clock = FakeClock()
        calls = []
        r = wait_until_healthy(url='u', is_alive=lambda: (False, 1), timeout_seconds=30, interval_seconds=1,
                               http_get=lambda u, t: calls.append(u) or 200, sleep=clock.sleep, clock=clock)
        self.assertFalse(r.ok)
        self.assertIn('exit code 1', r.detail)
        self.assertEqual(calls, [])  # never probed a dead container
        self.assertEqual(clock.now, 0.0)

    def test_times_out_within_budget(self):
        clock = FakeClock()
        r = wait_until_healthy(url='u', is_alive=lambda: (True, None), timeout_seconds=30, interval_seconds=1,
                               http_get=lambda u, t: (_ for _ in ()).throw(ConnectionRefusedError()),
                               sleep=clock.sleep, clock=clock)
        self.assertFalse(r.ok)
        self.assertLessEqual(clock.now, 30.0)
        self.assertGreaterEqual(r.attempts, 30)


class TestExternalUrl(unittest.TestCase):
    def test_template(self):
        self.assertEqual(external_preview_url('prv_1', TEMPLATE), 'https://prv-1.preview.148ai.com')  # DNS-safe label: '_' cannot be certified

    def test_never_localhost(self):
        for bad in (None, '', 'https://preview.148ai.com', 'http://localhost:8000/{preview_id}',
                    'http://127.0.0.1/{preview_id}', 'http://{preview_id}.localhost',
                    'ftp://{preview_id}.x.com', 'http://0.0.0.0/{preview_id}', '{preview_id}'):
            with self.subTest(bad=bad), self.assertRaises(PreviewBackendUnavailable):
                external_preview_url('prv_1', bad)


# ===========================================================================
# STEP 5 -- memory-only workspace rejected
# ===========================================================================

class TestDurableWorkspaceRequired(unittest.TestCase):
    def test_memory_workspace_rejected_for_previews(self):
        for ws in (MemoryProjectWorkspace(), ProjectWorkspace()):
            with self.assertRaises(PreviewBackendUnavailable) as ctx:
                ensure_durable_workspace(ws)
            self.assertIn('MemoryProjectWorkspace', str(ctx.exception))

    def test_postgres_workspace_accepted(self):
        ensure_durable_workspace(PostgresProjectWorkspace(pool=None, artifact_store=None))

    def test_launch_task_fails_closed_on_memory_workspace(self):
        repo, provider = FakePreviewRepo(), FakeProvider()
        status = worker_tasks._run_preview_launch(
            'prv_1', 'k', 'v', repo=repo, provider=provider, runtime_host='h1', url_template=TEMPLATE,
            probe_host='127.0.0.1', preflight=lambda: ensure_durable_workspace(MemoryProjectWorkspace()))
        self.assertEqual(status, 'FAILED')
        self.assertEqual(repo.status, 'FAILED')
        self.assertIn('MemoryProjectWorkspace', repo.error)
        self.assertEqual(provider.events, [])  # nothing started


# ===========================================================================
# STEP 4/5 -- launch + stop state machine (RUNNING only after probe)
# ===========================================================================

class FakePreviewRepo:
    """In-memory implementation of the PostgresPreviewRepository methods the
    worker uses, with the same STARTING-conditional semantics."""

    def __init__(self, status='STARTING'):
        self.status = status
        self.error = None
        self.url = None
        self.runtime = None
        self.cleaned = False
        self.events: list[str] = []

    def record_runtime(self, preview_id, **kw):
        self.events.append('record_runtime')
        if self.status != 'STARTING':
            return False
        self.runtime = kw
        return True

    def mark_running(self, preview_id, *, url):
        self.events.append('mark_running')
        if self.status != 'STARTING':
            return False
        self.status, self.url = 'RUNNING', url
        return True

    def mark_failed(self, preview_id, *, error, status='FAILED'):
        self.events.append(f'mark_failed:{status}')
        if self.status != 'STARTING':
            return False
        self.status, self.error = status, error
        return True

    def mark_cleaned(self, preview_id):
        self.cleaned = True

    def get_runtime(self, preview_id):
        rt = self.runtime or {}
        return {'status': self.status, 'container_id': rt.get('container_id'), 'runtime_host': rt.get('runtime_host'),
                'workdir': rt.get('workdir'), 'cleaned_at': 'x' if self.cleaned else None}


class FakeProvider:
    def __init__(self, *, start_exc=None, alive=(True, None), logs='boot log line'):
        self.start_exc = start_exc
        self.alive = alive
        self._logs = logs
        self.events: list[str] = []

    def start(self, **kw):
        self.events.append('start')
        if self.start_exc:
            raise self.start_exc
        return StartedPreview('cid1', 45678, '/tmp/omni-preview-prv_1-abc', contract(health_path='/healthz'))

    def is_running(self, cid):
        return self.alive

    def stop(self, cid):
        self.events.append(f'stop:{cid}')

    def logs(self, cid, tail=50):
        return self._logs

    def remove_workdir(self, path):
        self.events.append(f'rmdir:{path}')
        return True


class TestPreviewLaunch(unittest.TestCase):
    def launch(self, repo, provider, http_get, **kw):
        clock = FakeClock()
        probes = []

        def recording_get(url, timeout):
            probes.append(url)
            repo.events.append('probe')
            return http_get(url, timeout)

        status = worker_tasks._run_preview_launch(
            'prv_1', 'key', 'ver', repo=repo, provider=provider, runtime_host='worker-a',
            url_template=kw.pop('url_template', TEMPLATE), probe_host='127.0.0.1', probe_timeout=10,
            probe_interval=1, http_get=recording_get, sleep=clock.sleep, clock=clock, **kw)
        return status, probes

    def test_running_only_after_probe_succeeds(self):
        repo, provider = FakePreviewRepo(), FakeProvider()
        answers = [ConnectionRefusedError(), 200]

        def http_get(url, timeout):
            a = answers.pop(0)
            if isinstance(a, Exception):
                raise a
            return a

        status, probes = self.launch(repo, provider, http_get)
        self.assertEqual(status, 'RUNNING')
        self.assertEqual(repo.status, 'RUNNING')
        self.assertEqual(repo.events, ['record_runtime', 'probe', 'probe', 'mark_running'])
        self.assertEqual(probes[-1], 'http://127.0.0.1:45678/healthz')
        # persisted URL is the external route, never the worker's local port
        self.assertEqual(repo.url, 'https://prv-1.preview.148ai.com')  # DNS-safe label: '_' cannot be certified
        self.assertNotIn('127.0.0.1', repo.url)
        self.assertEqual(repo.runtime, {'container_id': 'cid1', 'runtime_host': 'worker-a', 'host_port': 45678,
                                        'workdir': '/tmp/omni-preview-prv_1-abc', 'data_storage': 'temporary'})
        self.assertNotIn('stop:cid1', provider.events)

    def test_probe_failure_is_failed_with_logs_and_full_teardown(self):
        repo, provider = FakePreviewRepo(), FakeProvider(logs='Traceback: ModuleNotFoundError: flask')
        status, _ = self.launch(repo, provider, lambda u, t: 503)
        self.assertEqual(status, 'FAILED')
        self.assertEqual(repo.status, 'FAILED')
        self.assertNotIn('mark_running', repo.events)
        self.assertIn('HTTP 503', repo.error)
        self.assertIn('ModuleNotFoundError: flask', repo.error)
        self.assertEqual(provider.events, ['start', 'stop:cid1', 'rmdir:/tmp/omni-preview-prv_1-abc'])
        self.assertTrue(repo.cleaned)

    def test_container_exit_is_failed_without_waiting(self):
        repo, provider = FakePreviewRepo(), FakeProvider(alive=(False, 2))
        status, probes = self.launch(repo, provider, lambda u, t: 200)
        self.assertEqual((status, repo.status, probes), ('FAILED', 'FAILED', []))
        self.assertIn('exit code 2', repo.error)
        self.assertIn('stop:cid1', provider.events)

    def test_crash_before_port_published_reports_exit_code_and_logs(self):
        repo = FakePreviewRepo()
        provider = FakeProvider(alive=(False, 3), logs='fatal: config missing')
        crashed = StartedPreview('cid1', None, '/tmp/omni-preview-prv_1-abc', contract())
        provider.start = lambda **kw: (provider.events.append('start'), crashed)[1]
        status, probes = self.launch(repo, provider, lambda u, t: 200)
        self.assertEqual((status, repo.status, probes), ('FAILED', 'FAILED', []))
        self.assertIn('exit code 3', repo.error)
        self.assertIn('fatal: config missing', repo.error)
        self.assertEqual(provider.events, ['start', 'stop:cid1', 'rmdir:/tmp/omni-preview-prv_1-abc'])

    def test_not_previewable_is_its_own_terminal_state(self):
        repo, provider = FakePreviewRepo(), FakeProvider(start_exc=NotPreviewable('runtime not allowed'))
        status, _ = self.launch(repo, provider, lambda u, t: 200)
        self.assertEqual((status, repo.status), ('NOT_PREVIEWABLE', 'NOT_PREVIEWABLE'))
        self.assertEqual(provider.events, ['start'])

    def test_docker_start_error_is_failed_and_reraised(self):
        repo, provider = FakePreviewRepo(), FakeProvider(start_exc=RuntimeError('docker run failed (exit 125)'))
        with self.assertRaises(RuntimeError):
            self.launch(repo, provider, lambda u, t: 200)
        self.assertEqual(repo.status, 'FAILED')
        self.assertIn('exit 125', repo.error)

    def test_missing_domain_template_fails_before_starting_anything(self):
        repo, provider = FakePreviewRepo(), FakeProvider()
        status, _ = self.launch(repo, provider, lambda u, t: 200, url_template=None)
        self.assertEqual((status, repo.status, provider.events), ('FAILED', 'FAILED', []))
        self.assertIn('PREVIEW_DOMAIN_TEMPLATE', repo.error)

    def test_user_stop_during_probe_wins_and_container_is_removed(self):
        repo, provider = FakePreviewRepo(), FakeProvider()

        def http_get(url, timeout):
            repo.status = 'STOPPED'  # DELETE landed while probing
            return 200

        status, _ = self.launch(repo, provider, http_get)
        self.assertEqual((status, repo.status), ('STOPPED', 'STOPPED'))
        self.assertIsNone(repo.url)
        self.assertEqual(provider.events, ['start', 'stop:cid1', 'rmdir:/tmp/omni-preview-prv_1-abc'])

    def test_user_stop_before_runtime_recorded(self):
        repo, provider = FakePreviewRepo(status='STOPPED'), FakeProvider()
        status, probes = self.launch(repo, provider, lambda u, t: 200)
        self.assertEqual((status, probes), ('STOPPED', []))
        self.assertIn('stop:cid1', provider.events)


class TestPreviewStop(unittest.TestCase):
    def repo(self, status, host='worker-a', cleaned=False):
        r = FakePreviewRepo(status=status)
        r.runtime = {'container_id': 'cid1', 'runtime_host': host, 'workdir': '/tmp/omni-preview-prv_1-abc'}
        r.cleaned = cleaned
        return r

    def test_stopped_preview_is_cleaned(self):
        repo, provider = self.repo('STOPPED'), FakeProvider()
        out = worker_tasks._run_preview_stop('prv_1', repo=repo, provider=provider, this_host='worker-a')
        self.assertTrue(out['cleaned'])
        self.assertEqual(provider.events, ['stop:cid1', 'rmdir:/tmp/omni-preview-prv_1-abc'])
        self.assertTrue(repo.cleaned)

    def test_never_tears_down_a_running_preview(self):
        for status in ('RUNNING', 'STARTING'):
            repo, provider = self.repo(status), FakeProvider()
            out = worker_tasks._run_preview_stop('prv_1', repo=repo, provider=provider, this_host='worker-a')
            self.assertFalse(out['cleaned'])
            self.assertEqual(provider.events, [])

    def test_wrong_host_raises_instead_of_pretending(self):
        repo, provider = self.repo('STOPPED', host='worker-b'), FakeProvider()
        with self.assertRaises(RuntimeError):
            worker_tasks._run_preview_stop('prv_1', repo=repo, provider=provider, this_host='worker-a')
        self.assertEqual((provider.events, repo.cleaned), ([], False))

    def test_already_cleaned_is_noop(self):
        repo, provider = self.repo('STOPPED', cleaned=True), FakeProvider()
        worker_tasks._run_preview_stop('prv_1', repo=repo, provider=provider, this_host='worker-a')
        self.assertEqual(provider.events, [])


class TestQueues(unittest.TestCase):
    def test_host_queue_name(self):
        self.assertEqual(preview_host_queue('worker-a'), 'omni-preview-host-worker-a')
        self.assertEqual(preview_host_queue('ip 10.0.0.5/x'), 'omni-preview-host-ip-10.0.0.5-x')
        with self.assertRaises(ValueError):
            preview_host_queue('  ')

    def test_enqueue_build_routes_to_named_queue_and_passes_all_args(self):
        with patch('omni_prod.queueing.queue') as q:
            enqueue_build('redis://x', 'omni_prod.worker_tasks.stop_preview_task', 'prv_1',
                          job_id='j', queue_name='omni-preview-host-a')
            q.assert_called_once_with('redis://x', 'omni-preview-host-a')
            args, kwargs = q.return_value.enqueue.call_args
            self.assertEqual(args, ('omni_prod.worker_tasks.stop_preview_task', 'prv_1'))
            self.assertEqual(kwargs['job_id'], 'j')

    def test_enqueue_build_default_queue_unchanged(self):
        with patch('omni_prod.queueing.queue') as q:
            enqueue_build('redis://x', 'f', 'b1', job_id='b1')
            q.assert_called_once_with('redis://x', BUILD_QUEUE)


# ===========================================================================
# Fake Postgres pool (mirrors omni_prod/db.py DatabasePool's contract)
# ===========================================================================

class ScriptedCursor:
    def __init__(self, fetch=(), rowcounts=()):
        self.executed: list[tuple[str, object]] = []
        self._fetch = list(fetch)
        self._rowcounts = list(rowcounts)
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.executed.append((' '.join(sql.split()), params))
        self.rowcount = self._rowcounts.pop(0) if self._rowcounts else 1

    def fetchone(self):
        return self._fetch.pop(0) if self._fetch else None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Ctx:
    def __init__(self, value=None):
        self.value = value

    def __enter__(self):
        return self.value if self.value is not None else self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self, cur):
        self.cur = cur
        self.transactions = 0

    def cursor(self):
        return self.cur

    def transaction(self):
        self.transactions += 1
        return _Ctx()


class FakePool:
    def __init__(self, cur):
        self.conn = FakeConn(cur)

    def connection(self):
        return _Ctx(self.conn)


class TestPreviewRepositorySql(unittest.TestCase):
    def repo(self, **kw):
        cur = ScriptedCursor(**kw)
        return PostgresPreviewRepository(FakePool(cur)), cur

    def test_create_uses_make_interval(self):
        r, cur = self.repo()
        r.create('prv_1', 'k', 'v', ttl_seconds=3600)
        sql, params = cur.executed[0]
        self.assertIn('make_interval(secs => %s)', sql)
        self.assertNotIn('||', sql)
        self.assertEqual(params, ('prv_1', 'k', 'v', 3600))
        with self.assertRaises(ValueError):
            r.create('prv_1', 'k', 'v', ttl_seconds=0)

    def test_launch_writes_are_conditional_on_starting(self):
        r, cur = self.repo(rowcounts=[1, 0, 1, 0])
        self.assertTrue(r.record_runtime('p', container_id='c', runtime_host='h', host_port=5, workdir='/w'))
        self.assertFalse(r.mark_running('p', url='https://p.x'))
        self.assertTrue(r.mark_failed('p', error='boom'))
        self.assertFalse(r.mark_failed('p', error='x', status='NOT_PREVIEWABLE'))
        for sql, _ in cur.executed:
            self.assertIn("AND status = 'STARTING'", sql)
        self.assertEqual(cur.executed[1][1], ('https://p.x', 'p'))
        with self.assertRaises(ValueError):
            r.mark_failed('p', error='x', status='RUNNING')

    def test_request_stop_running(self):
        r, cur = self.repo(fetch=[('RUNNING', 'worker-a', None)])
        out = r.request_stop('prv_1', 'k')
        self.assertEqual(out, {'status': 'STOPPED', 'changed': True, 'runtime_host': 'worker-a', 'needs_cleanup': True})
        self.assertIn('FOR UPDATE', cur.executed[0][0])
        self.assertEqual(cur.executed[0][1], ('prv_1', 'k'))  # tenant-scoped
        self.assertIn("SET status = 'STOPPED'", cur.executed[1][0])

    def test_request_stop_terminal_is_idempotent(self):
        r, cur = self.repo(fetch=[('FAILED', None, None)])
        out = r.request_stop('prv_1', 'k')
        self.assertEqual((out['status'], out['changed'], out['needs_cleanup']), ('FAILED', False, False))
        self.assertEqual(len(cur.executed), 1)  # no UPDATE

    def test_request_stop_retry_redispatches_uncleaned(self):
        r, _ = self.repo(fetch=[('STOPPED', 'worker-a', None)])
        out = r.request_stop('prv_1', 'k')
        self.assertEqual((out['changed'], out['needs_cleanup']), (False, True))

    def test_request_stop_expired_container_gets_cleaned(self):
        r, _ = self.repo(fetch=[('EXPIRED', 'worker-a', None)])
        self.assertTrue(r.request_stop('prv_1', 'k')['changed'])

    def test_request_stop_unknown_raises(self):
        r, _ = self.repo(fetch=[None])
        with self.assertRaises(KeyError):
            r.request_stop('prv_x', 'k')

    def test_get_is_tenant_scoped(self):
        from datetime import datetime, timezone
        t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        r, cur = self.repo(fetch=[('prv_1', 'k', 'v', 'RUNNING', 'https://prv_1.x', 'cid', None, t, t,
                                   'worker-a', 45678, '/tmp/omni-preview-a', None, None)])
        out = r.get('prv_1', 'k')
        self.assertEqual((out['status'], out['host_port'], out['created_at']), ('RUNNING', 45678, '2026-01-01T00:00:00+00:00'))
        self.assertEqual(cur.executed[0][1], ('prv_1', 'k'))
        r2, _ = self.repo(fetch=[None])
        with self.assertRaises(KeyError):
            r2.get('prv_1', 'other-tenant')

    def test_get_route_only_running_unexpired(self):
        r, cur = self.repo(fetch=[('worker-a', 45678)])
        self.assertEqual(r.get_route('prv_1'), ('worker-a', 45678))
        self.assertIn("status = 'RUNNING' AND expires_at > now()", cur.executed[0][0])
        r2, _ = self.repo(fetch=[None])
        self.assertIsNone(r2.get_route('prv_1'))

    def test_mark_expired(self):
        r, cur = self.repo(rowcounts=[3])
        self.assertEqual(r.mark_expired(), 3)
        self.assertIn("WHERE status = 'RUNNING' AND expires_at < now()", cur.executed[0][0])


# ===========================================================================
# STEP 1 -- M1 billing, gates, outbox
# ===========================================================================

def real_spend_gateway(calls: int, per_call: str) -> SimpleNamespace:
    """A gateway-shaped object whose spend ledger was produced by the real
    model_policy.authorize_model_call(), exactly as RoutedModelGateway does."""
    state = ModelUseState()
    policy = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                            external_budget_usd=Decimal('10'), max_external_calls_per_build=10)
    ext = ModelEndpoint(name='ext', base_url='https://api.example', model='m', api_key='k', external=True)
    local = ModelEndpoint(name='local', base_url='http://127.0.0.1:1', model='m')
    authorize_model_call(endpoint=local, policy=policy, state=state, estimated_cost_usd=Decimal('0'))
    for _ in range(calls):
        authorize_model_call(endpoint=ext, policy=policy, state=state, estimated_cost_usd=Decimal(per_call))
    return SimpleNamespace(state=state, events=[])


class TestBillingRules(unittest.TestCase):
    def test_spend_ledger_is_real(self):
        self.assertEqual(worker_tasks.spend_snapshot(real_spend_gateway(2, '0.25')), (Decimal('0.50'), 2))
        self.assertEqual(worker_tasks.spend_snapshot(real_spend_gateway(0, '0.25')), (Decimal('0'), 0))
        self.assertEqual(worker_tasks.spend_snapshot(None), (Decimal('0'), 0))

    def test_rules(self):
        cases = [
            (True, Decimal('0'), 0, 'settled', Decimal('0')),
            (True, Decimal('0.5'), 2, 'settled', Decimal('0.5')),
            (False, Decimal('0.5'), 2, 'settled', Decimal('0.5')),
            (False, Decimal('0'), 1, 'settled', Decimal('0')),
            (False, Decimal('0'), 0, 'released', None),
        ]
        for ready, spent, calls, expected, settle_amount in cases:
            with self.subTest(ready=ready, spent=spent, calls=calls):
                subs = MagicMock()
                self.assertEqual(worker_tasks.resolve_billing(subs, build_id='b', ready=ready, spent=spent,
                                                              external_calls=calls), expected)
                if expected == 'settled':
                    subs.settle.assert_called_once_with(build_id='b', actual_provider_cost_usd=settle_amount)
                    subs.release.assert_not_called()
                else:
                    subs.release.assert_called_once_with(build_id='b')
                    subs.settle.assert_not_called()


class FakeJobs:
    def __init__(self, request=None, claim=True):
        self.request = request or {
            'user_id': 'u1', 'internal_project_id': 'tenant_abc', 'prompt': 'Build a todo app',
            'target_markets': ('US',), 'branding_visible': None, 'white_label_name': None,
            'rights_evidence': [RightsEvidence('ev1', RightKind.TRADEMARK, 'Acme', 'license', 'global').to_dict()],
            'public_project_id': 'proj_public',
        }
        self.claim = claim
        self.transitions: list[dict] = []

    def get_request(self, build_id):
        return self.request

    def transition(self, **kw):
        self.transitions.append(kw)
        return self.claim if kw['target'] == BuildStatus.RUNNING else True


def _gate(passed, **extra):
    d = {'passed': passed, **extra}
    return SimpleNamespace(passed=passed, to_dict=lambda: d, **extra)


class BuildHarness:
    def __init__(self, *, verified=True, quality=True, security=True, rights_clear=True,
                 calls=0, engine_exc=None, factory_exc=None, preflight=None):
        self.jobs = FakeJobs()
        self.subs = MagicMock()
        self.subs.plan_for.return_value = SimpleNamespace(code='pro')
        self.platform = MagicMock()
        self.platform.subscriptions = self.subs
        self.platform.brain.decide.return_value = SimpleNamespace(
            rights=SimpleNamespace(required_disclosures=()), creative='creative-plan')
        self.platform.brain.creative.repository_files.return_value = {'.148ai/creative.json': '{}'}
        rights_status = GateStatus.CLEAR if rights_clear else GateStatus.REVIEW
        self.platform.rights.assess.return_value = SimpleNamespace(
            publish_allowed=rights_clear, status=rights_status, to_dict=lambda: {'status': rights_status.value})
        self.platform.rights.repository_files.return_value = {'RIGHTS.md': 'r'}
        self.platform.branding.decorate_repository.side_effect = lambda repo, **kw: {**repo, '.148ai/brand.json': '{}'}
        self.workspace = MagicMock()
        self.workspace.commit.return_value = SimpleNamespace(id='ver_1', artifact_key='repositories/abc.zip')
        self.gateway = real_spend_gateway(calls, '0.25')
        report = ExecutionReport(passed=verified, failures=() if verified else (AcceptanceFailure('AC-1', 'tests failed', 'E'),),
                                 build_log='log')
        self.result = SimpleNamespace(status='ready' if verified else 'failed', spec=ACCEPTED_SPEC,
                                      repository={'app.py': 'x', '.omni/project.json': '{}'}, repair_rounds=1, report=report)
        self.engine = MagicMock()
        self.engine.executor = verified_chain()  # release policy: checks ran and passed
        if engine_exc:
            self.engine.build.side_effect = engine_exc
        else:
            self.engine.build.return_value = self.result
        self.factory_exc = factory_exc
        self.quality = _gate(quality, score=90 if quality else 40, minimum_score=80, blockers=() if quality else ('no tests',))
        self.security = _gate(security, findings=() if security else ('secret',))
        self.preflight = preflight

    def factory(self):
        if self.factory_exc:
            raise self.factory_exc
        return self.engine, self.gateway

    def run(self):
        return worker_tasks._run_live_build_job(
            'bld_1', jobs=self.jobs, platform=self.platform, workspace=self.workspace,
            components_factory=self.factory, quality_fn=lambda **kw: self.quality,
            security_fn=lambda repo: self.security, preflight=self.preflight)

    @property
    def final(self):
        return self.jobs.transitions[-1]


class TestAsyncBuildGatesAndBilling(unittest.TestCase):
    def test_all_gates_pass_is_ready_and_settled_at_real_spend(self):
        h = BuildHarness(calls=2)
        self.assertEqual(h.run(), 'ready')
        self.assertEqual(h.final['target'], BuildStatus.READY)
        self.assertEqual(h.final['result_version_id'], 'ver_1')
        self.assertEqual(h.final['actual_provider_cost_usd'], Decimal('0.50'))
        h.subs.settle.assert_called_once_with(build_id='bld_1', actual_provider_cost_usd=Decimal('0.50'))
        h.subs.release.assert_not_called()
        ev = h.final['evidence_json']
        self.assertEqual(set(ev['gates']), {'verification', 'quality', 'security', 'rights'})
        self.assertTrue(ev['release_ready'])
        self.assertIn('authorized', ev['provider_spend_basis'])

    def test_committed_repo_matches_canonical_live_build(self):
        h = BuildHarness()
        h.run()
        committed = h.workspace.commit.call_args.kwargs
        self.assertEqual(committed['project_id'], 'tenant_abc')
        self.assertEqual(set(committed['repository']),
                         {'app.py', '.omni/project.json', '.148ai/creative.json', 'RIGHTS.md', '.148ai/brand.json'})
        deco = h.platform.branding.decorate_repository.call_args.kwargs
        self.assertEqual((deco['project_id'], deco['plan']), ('proj_public', 'pro'))
        rights_kw = h.platform.rights.assess.call_args.kwargs
        self.assertEqual(rights_kw['target_markets'], ('US',))
        self.assertIsInstance(rights_kw['evidence'][0], RightsEvidence)  # rebuilt from JSONB dicts
        self.assertEqual(rights_kw['evidence'][0].right_kind, RightKind.TRADEMARK)

    def test_gate_failures_in_order(self):
        cases = [
            (dict(verified=False), 'verification_failed'),
            (dict(quality=False), 'quality_gate_failed'),
            (dict(security=False), 'security_gate_failed'),
            (dict(rights_clear=False), 'rights_gate_not_clear'),
            (dict(verified=False, quality=False, security=False, rights_clear=False), 'verification_failed'),
            (dict(quality=False, rights_clear=False), 'quality_gate_failed'),
        ]
        for kwargs, code in cases:
            with self.subTest(**kwargs):
                h = BuildHarness(**kwargs)
                self.assertEqual(h.run(), 'failed')
                self.assertEqual((h.final['target'], h.final['error_code']), (BuildStatus.FAILED, code))
                self.assertFalse(h.final['evidence_json']['release_ready'])
                # Decision change 2026-10-07 (Golden E2E #1): a failed build is not a
                # project version -- it became "current" and the next modification
                # ran against the failed product. Only a rights-only block (code
                # passed, evidence missing) is still committed.
                if code == 'rights_gate_not_clear':
                    self.assertEqual(h.final['result_version_id'], 'ver_1')
                else:
                    self.assertIsNone(h.final['result_version_id'])
                    h.workspace.commit.assert_not_called()

    def test_failed_build_without_external_spend_releases(self):
        h = BuildHarness(quality=False, calls=0)
        h.run()
        h.subs.release.assert_called_once_with(build_id='bld_1')
        h.subs.settle.assert_not_called()
        self.assertEqual(h.final['evidence_json']['billing'], 'released')

    def test_failed_build_with_external_spend_settles_not_releases(self):
        h = BuildHarness(security=False, calls=3)
        h.run()
        h.subs.settle.assert_called_once_with(build_id='bld_1', actual_provider_cost_usd=Decimal('0.75'))
        h.subs.release.assert_not_called()

    def test_exception_after_spend_settles_and_reraises(self):
        h = BuildHarness(calls=2)
        h.platform.branding.decorate_repository.side_effect = PermissionError('white-label requires Business')
        with self.assertRaises(PermissionError):
            h.run()
        self.assertEqual((h.final['target'], h.final['error_code']), (BuildStatus.FAILED, 'worker_exception'))
        h.subs.settle.assert_called_once_with(build_id='bld_1', actual_provider_cost_usd=Decimal('0.50'))
        h.subs.release.assert_not_called()

    def test_exception_before_any_spend_releases_and_reraises(self):
        h = BuildHarness(factory_exc=RuntimeError('OMNI_ENABLE_LIVE_BUILD=1 is required'))
        with self.assertRaises(RuntimeError):
            h.run()
        h.subs.release.assert_called_once_with(build_id='bld_1')
        h.subs.settle.assert_not_called()
        self.assertIn('OMNI_ENABLE_LIVE_BUILD', h.final['error_message'])

    def test_memory_workspace_worker_fails_build_and_releases(self):
        h = BuildHarness(preflight=lambda: ensure_durable_workspace(MemoryProjectWorkspace(),
                                                                     purpose='Durable async build'))
        with self.assertRaises(PreviewBackendUnavailable):
            h.run()
        self.assertEqual(h.final['target'], BuildStatus.FAILED)
        h.subs.release.assert_called_once()
        h.engine.build.assert_not_called()

    def test_duplicate_delivery_is_noop(self):
        h = BuildHarness()
        h.jobs.claim = False
        self.assertIsNone(h.run())
        h.engine.build.assert_not_called()
        h.subs.settle.assert_not_called()
        h.subs.release.assert_not_called()


class TestOutboxRelay(unittest.TestCase):
    def test_dispatches_pending_rows_one_transaction_each(self):
        cur = ScriptedCursor(fetch=[('bld_1',), ('bld_2',), None])
        pool = FakePool(cur)
        sent = []
        out = PostgresBuildRepository(pool).dispatch_pending_outbox(sent.append, older_than_seconds=30)
        self.assertEqual((out, sent), (['bld_1', 'bld_2'], ['bld_1', 'bld_2']))
        selects = [s for s, _ in cur.executed if s.startswith('SELECT')]
        updates = [p for s, p in cur.executed if s.startswith('UPDATE build_outbox')]
        self.assertTrue(all('FOR UPDATE SKIP LOCKED' in s and 'enqueued_at IS NULL' in s for s in selects))
        self.assertEqual(updates, [('bld_1',), ('bld_2',)])
        self.assertEqual(pool.conn.transactions, 3)

    def test_enqueue_failure_leaves_row_pending(self):
        cur = ScriptedCursor(fetch=[('bld_1',)])

        def down(build_id):
            raise ConnectionError('redis down')

        with self.assertRaises(ConnectionError):
            PostgresBuildRepository(FakePool(cur)).dispatch_pending_outbox(down)
        self.assertFalse(any(s.startswith('UPDATE') for s, _ in cur.executed))

    def test_limit(self):
        cur = ScriptedCursor(fetch=[('a',), ('b',), ('c',)])
        out = PostgresBuildRepository(FakePool(cur)).dispatch_pending_outbox(lambda b: None, limit=2)
        self.assertEqual(out, ['a', 'b'])


if __name__ == '__main__':
    unittest.main()
