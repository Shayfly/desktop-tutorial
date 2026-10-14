"""M4.9 directive item 7 -- "CLEAN-ROOM SUCCESS RUN": at least one fresh
end-to-end execution using a fresh isolated test database, cleared Redis/RQ
state, and the freshly built + provenance-documented local sandbox image
(omni-sandbox:latest, digest
sha256:97f2424d071002cc082e3f0fb924669bea0a44787cde2d13938041e27eab3ccf --
see PATCH_APPLICATION_REPORT.md's M4.9 section), with no candidate/version
artifacts reused from any previous test run.

This reuses the exact, already-disclosed M4D.2b real-infrastructure harness
(tests/m4d2b_worker_process.py -- a genuinely separate OS process running a
real rq.Worker; tests/m4d2b_local_model_server.py -- a real local HTTP
server standing in for a hosted LLM at the codebase's own documented
"local-first" gateway boundary) but differs from every existing test in
this repository in one required way: this is the FIRST test, anywhere in
this codebase, that drives a ModificationRequest to a genuine
READY_FOR_REVIEW using the REAL classify() -> real free-repair loop -> REAL
`docker run omni-sandbox:latest ...` sandbox verification -> real quality
gate -> real security scan -> real rights gate, with NO manual
`PostgresModificationRepository.complete(status='READY_FOR_REVIEW', ...)`
shortcut anywhere (contrast tests/test_m4d2_live_fastapi_redis.py's
`test_full_http_propose_accept_flow_persists_to_real_postgres`, which
explicitly documents taking that shortcut because no working sandbox image
existed yet at that time; M4.9 built one -- see task #48).

Isolation from every other live-infra test file in this repo:
  - a dedicated fresh Postgres database (M49_DATABASE_URL, default
    m49_clean_room -- NOT m4d2_test, which earlier milestones' tests write
    to), created and migrated by this run (see
    PATCH_APPLICATION_REPORT.md's M4.9 section for the exact
    `DROP DATABASE IF EXISTS` / `CREATE DATABASE` / migration-apply
    commands run immediately before this file, and their output showing
    all relevant tables at 0 rows beforehand).
  - Redis FLUSHALL immediately before this run (also recorded in
    PATCH_APPLICATION_REPORT.md's M4.9 section).
  - its own dedicated local-model-server port and its own dedicated
    tempdir artifact root, so it shares no queue, no database, and no
    on-disk artifact state with any other test file's run.

Must run standalone (own process) -- same reason as
tests/test_m4d2_live_fastapi_redis.py and
tests/test_m4d2b_parity_and_worker.py: importing omni_prod.investor_app
bakes module-level globals (_v28, _v28_pool) from whatever
OMNI_CREATOR_PERSISTENCE/OMNI_DATABASE_URL were set at first import in this
process:
  M49_DATABASE_URL=postgresql://postgres:m4d2pass@127.0.0.1:5432/m49_clean_room \\
  PYTHONPATH=/tmp/m4d2b_vendor:/tmp/m49_pytest_vendor \\
  python3.11 -m pytest -q tests/test_m49_clean_room.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import subprocess
import tempfile
import unittest
import uuid


def _skip_reason() -> str | None:
    try:
        import psycopg  # noqa: F401
        import fastapi  # noqa: F401
        import redis  # noqa: F401
        import rq  # noqa: F401
    except ImportError as exc:
        return f'live-infra dependency not importable ({exc})'
    database_url = os.environ.get('M49_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m49_clean_room')
    redis_url = os.environ.get('M49_REDIS_URL', 'redis://127.0.0.1:6379/0')
    try:
        conn = psycopg.connect(database_url, connect_timeout=3)
        conn.close()
    except Exception as exc:  # pragma: no cover - environment probe
        return f'cannot reach the fresh clean-room Postgres at {database_url!r}: {exc}'
    try:
        redis.Redis.from_url(redis_url, socket_connect_timeout=3).ping()
    except Exception as exc:  # pragma: no cover - environment probe
        return f'cannot reach live Redis at {redis_url!r}: {exc}'
    if not shutil.which('docker'):
        return 'docker binary not found -- required for the real omni-sandbox:latest run'
    out = subprocess.run(['docker', 'inspect', '--format={{.Id}}', 'omni-sandbox:latest'],
                          capture_output=True, text=True)
    if out.returncode != 0:
        return f'omni-sandbox:latest not present: {out.stderr.strip()}'
    if 'omni_prod.investor_app' in sys.modules:
        return ('omni_prod.investor_app was already imported by another test module in this '
                'process -- run this file standalone: python3 -m pytest -q tests/test_m49_clean_room.py')
    return None


_SKIP = _skip_reason()

DATABASE_URL = os.environ.get('M49_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m49_clean_room')
REDIS_URL = os.environ.get('M49_REDIS_URL', 'redis://127.0.0.1:6379/0')
_BILLING_ADMIN_KEY = 'm49-clean-room-billing-admin-key'
_ARTIFACT_ROOT = tempfile.mkdtemp(prefix='m49_clean_room_artifacts_')
_MODEL_SERVER_PORT = int(os.environ.get('M49_MODEL_SERVER_PORT', '8099'))
_MODEL_SERVER_URL = f'http://127.0.0.1:{_MODEL_SERVER_PORT}/v1'

if _SKIP is None:
    os.environ['OMNI_CREATOR_PERSISTENCE'] = 'postgres'
    os.environ['OMNI_DATABASE_URL'] = DATABASE_URL
    os.environ['OMNI_REDIS_URL'] = REDIS_URL
    os.environ['OMNI_BILLING_ADMIN_KEY'] = _BILLING_ADMIN_KEY
    os.environ.setdefault('OMNI_SECRET_KEY', 'm49-clean-room-live-worker-secret-' + 'x' * 32)
    os.environ['OMNI_ENABLE_LIVE_BUILD'] = '1'
    os.environ['OMNI_LOCAL_MODEL_URL'] = _MODEL_SERVER_URL
    os.environ['M4D2B_ARTIFACT_ROOT'] = _ARTIFACT_ROOT  # tests/m4d2b_worker_process.py reads this exact name

    from fastapi.testclient import TestClient

    import omni_prod.investor_app as iapp
    from omni_prod.workspace import PostgresProjectWorkspace
    from tests.test_m4d2_live_postgres import DiskArtifactStore
    from tests.m4d2b_local_model_server import LocalModelServer

    assert iapp._v28_pool is not None, 'OMNI_CREATOR_PERSISTENCE=postgres must have wired a real DatabasePool'
    iapp._v28.engine.workspace = PostgresProjectWorkspace(iapp._v28_pool, DiskArtifactStore(_ARTIFACT_ROOT))


_WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), 'm4d2b_worker_process.py')
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_separate_worker_process(timeout: float = 90.0) -> subprocess.CompletedProcess:
    """Genuinely separate OS process, same harness as M4D.2b -- see
    tests/m4d2b_worker_process.py's own docstring for why a real rq.Worker
    (fork-per-job) has to run out-of-process here."""
    env = os.environ.copy()
    existing = os.environ.get('PYTHONPATH', '')
    env['PYTHONPATH'] = (_REPO_ROOT + os.pathsep + existing) if existing else _REPO_ROOT
    proc = subprocess.run(
        [sys.executable, _WORKER_SCRIPT, str(timeout - 10)],
        cwd=_REPO_ROOT, env=env, capture_output=True, text=True, timeout=timeout,
    )
    return proc


# A repository designed to genuinely pass every real gate
# (SandboxRepositoryExecutor -> real `docker run omni-sandbox:latest`,
# quality_gate.assess_repository, security_testing.hostile_repository_scan)
# under this container's real, minimal omni-sandbox:latest image, whose only
# interpreter is /usr/bin/python3.11 (no PATH-resolved "python3"/"pytest" --
# see PATCH_APPLICATION_REPORT.md's M4.9 provenance section for why the
# image has no shell/PATH-lookup surface and the verify command must name
# the interpreter by absolute path).
_SEED_INDEX_HTML = (
    '<html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>'
    '<body><h1 aria-label="Todo List">Todo List</h1><ul><li>Buy milk</li></ul></body></html>'
)
_SEED_README = '# Todo App\n\nMinimal todo list app used for the M4.9 clean-room verification run.\n'
_SEED_REQUIREMENTS = '# no external dependencies -- pure stdlib\n'
_SEED_TEST = (
    'import pathlib\n\n'
    'def test_todo_list_is_present():\n'
    '    html = pathlib.Path("index.html").read_text()\n'
    '    assert "Todo List" in html\n'
    '    assert "<li>" in html\n'
)
_SEED_MANIFEST = json.dumps({
    'build': [],
    'verify': [{
        'name': 'acceptance',
        'argv': ['/usr/bin/python3.11', '-m', 'pytest', '-q'],
        'acceptance_ids': ['A1'],
    }],
})


@unittest.skipIf(_SKIP, _SKIP)
class CleanRoomModificationLifecycleTests(unittest.TestCase):
    """Item 7's clean-room run, driving a genuine, non-mocked
    READY_FOR_REVIEW candidate through real Postgres + real Redis/RQ + the
    real freshly-built omni-sandbox:latest image."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(iapp.app)
        cls.model_server = LocalModelServer(port=_MODEL_SERVER_PORT).start()
        import redis
        cls.redis_conn = redis.Redis.from_url(REDIS_URL)

    @classmethod
    def tearDownClass(cls):
        cls.model_server.stop()

    def _register_and_upgrade(self) -> dict:
        email = f'm49-{uuid.uuid4().hex[:12]}@example.com'
        r = self.client.post('/api/v28/auth/register', json={'email': email, 'password': 'StrongPass123!'})
        self.assertEqual(r.status_code, 200, r.text)
        reg = r.json()
        up = self.client.post('/api/v28/admin/subscription',
                               headers={'X-148AI-Billing-Admin-Key': _BILLING_ADMIN_KEY},
                               json={'user_id': reg['user']['id'], 'plan': 'business'})
        self.assertEqual(up.status_code, 200, up.text)
        return reg

    def test_clean_room_real_pipeline_reaches_genuine_ready_for_review(self):
        reg = self._register_and_upgrade()
        h = {'Authorization': 'Bearer ' + reg['token']}
        pr = self.client.post('/api/v28/projects', headers=h, json={'title': 'M4.9 clean-room todo'})
        self.assertEqual(pr.status_code, 200, pr.text)
        project_id = pr.json()['id']
        _, key = iapp._v28.resolve_project_key(token=reg['token'], project_id=project_id)

        from omni_prod.product_spec import ProductSpec
        from omni_prod.spec_repository import PostgresSpecRepository
        spec = ProductSpec.from_dict({
            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
            'requirements': [{'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True}],
            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
        })
        version = iapp._v28.engine.workspace.commit(
            project_id=key,
            repository={
                'index.html': _SEED_INDEX_HTML,
                'README.md': _SEED_README,
                'requirements.txt': _SEED_REQUIREMENTS,
                'tests/test_seed.py': _SEED_TEST,
                '.omni/project.json': _SEED_MANIFEST,
            },
            message='m49 clean-room seed', expected_current_version_id=None)
        PostgresSpecRepository(iapp._v28_pool).save(version_id=version.id, project_id=key, spec=spec)

        # Sanity: the seed repository, run through the REAL sandbox executor
        # directly (bypassing the worker), must already pass on its own --
        # this isolates "does the fixture repo genuinely pass the real
        # sandbox" from "does the full worker pipeline reach READY_FOR_REVIEW",
        # so a failure in one is never masked by the other.
        from omni_prod.sandbox_executor import SandboxRepositoryExecutor
        from omni_prod.sandbox import SandboxLimits
        direct_report = SandboxRepositoryExecutor(limits=SandboxLimits()).execute(
            repository={
                'index.html': _SEED_INDEX_HTML, 'README.md': _SEED_README,
                'requirements.txt': _SEED_REQUIREMENTS, 'tests/test_seed.py': _SEED_TEST,
                '.omni/project.json': _SEED_MANIFEST,
            },
            spec=spec,
        )
        self.assertTrue(direct_report.passed, f'seed fixture must genuinely pass the real sandbox on its own: '
                                                f'{direct_report.build_log}')

        from omni_prod.queueing import BUILD_QUEUE
        import rq
        q = rq.Queue(BUILD_QUEUE, connection=self.redis_conn)

        propose = self.client.post(
            f'/api/v28/projects/{project_id}/versions/{version.id}/modifications', headers=h,
            json={'followup': 'M4D2B_CLASSIFY:missing_requirement M4D2B_IDS:A1 the acceptance check for the '
                              'todo list must keep passing after this fix'})
        self.assertEqual(propose.status_code, 202, propose.text)
        body = propose.json()
        self.assertEqual(body['dispatch'], 'enqueued')
        modification_id = body['modification_id']

        job = q.fetch_job(modification_id)
        self.assertIsNotNone(job, 'the real production enqueue must have created this real rq job')
        self.assertEqual(job.func_name, 'omni_prod.worker_tasks.execute_modification_job')
        self.assertFalse(job.is_finished)

        proc = _run_separate_worker_process()
        self.assertEqual(proc.returncode, 0,
                          f'separate worker process failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
        self.assertIn('M4D2B_WORKER_PROCESS_DONE ran=True', proc.stdout, proc.stdout + proc.stderr)

        job.refresh()
        self.assertTrue(job.is_finished, f'job status: {job.get_status()}; worker stderr:\n{proc.stderr}')

        status = self.client.get(f'/api/v28/projects/{project_id}/modifications/{modification_id}', headers=h)
        self.assertEqual(status.status_code, 200, status.text)
        d = status.json()
        self.assertEqual(d['status'], 'READY_FOR_REVIEW', d)
        self.assertEqual(d['classification'], 'missing_requirement', d)
        self.assertIsNone(d['promoted_version_id'], 'nothing is promoted until an explicit accept()')
        self.assertIsNotNone(d['completed_at'])

        evidence = d['evidence']
        self.assertTrue(evidence['verification']['passed'], evidence)
        self.assertEqual(evidence['verification']['failures'], [])
        self.assertTrue(evidence['gates']['passed'], evidence['gates'])
        self.assertIsNone(evidence['gates']['blocking_gate'])
        self.assertTrue(evidence['gates']['quality']['passed'], evidence['gates']['quality'])
        self.assertTrue(evidence['gates']['security']['passed'], evidence['gates']['security'])
        self.assertIsNotNone(evidence['diff'])

        candidate = self.client.get(
            f'/api/v28/projects/{project_id}/modifications/{modification_id}/candidate', headers=h)
        self.assertEqual(candidate.status_code, 200, candidate.text)
        cand = candidate.json()
        cand_paths = {f['path'] for f in cand['repository']['files']}
        self.assertIn('index.html', cand_paths)
        self.assertIn('.omni/project.json', cand_paths)
        self.assertIn('tests/test_seed.py', cand_paths)
        # M4D2B_NOTES.md -- real, disclosed evidence the free-repair loop's
        # real repair() call against the local model server genuinely ran
        # (round 1 always repairs before the first real verification; see
        # modifier_engine.run_free_repair) and its patch was really applied
        # via apply_patch() on top of the seed repository (additive, not
        # destructive -- every seed file is still present alongside it).
        self.assertIn('M4D2B_NOTES.md', cand_paths)
        self.assertEqual(cand['spec']['title'], 'Todo')

        # Item 10 / item 11 setup: verify directly against Postgres (not just
        # the HTTP view) that a real, non-orphaned candidate row exists and
        # that no version has been promoted yet -- current() is unchanged.
        from omni_prod.modification_repository import PostgresModificationRepository
        mods_repo = PostgresModificationRepository(iapp._v28_pool)
        details = mods_repo.get_details(modification_id, key)
        self.assertEqual(details.status, 'READY_FOR_REVIEW')
        db_candidate = mods_repo.get_candidate(modification_id, key)
        self.assertIn('index.html', db_candidate['repository'])
        self.assertIn('.omni/project.json', db_candidate['repository'])
        self.assertEqual(db_candidate['spec'].title, 'Todo')

        current = iapp._v28.engine.workspace.current(key)
        self.assertEqual(current.id, version.id, 'READY_FOR_REVIEW must not promote a version by itself')

        # Stash identifiers for tasks #50-#52 (negative security tests,
        # READY_FOR_REVIEW invariant re-verification, and the real
        # accept()+rollback() lifecycle) to reuse this SAME clean-room
        # database/modification rather than creating a second one.
        with open('/tmp/m49_clean_room_ids.json', 'w') as f:
            json.dump({
                'database_url': DATABASE_URL, 'project_id': project_id, 'project_key': key,
                'version_id': version.id, 'modification_id': modification_id,
                'token': reg['token'], 'user_id': reg['user']['id'],
                'billing_admin_key': _BILLING_ADMIN_KEY, 'artifact_root': _ARTIFACT_ROOT,
            }, f)


if __name__ == '__main__':
    unittest.main()
