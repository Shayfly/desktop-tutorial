"""M4D.2b -- items 2 and 3 of the "M4D.2b DEPENDENCY PARITY + REAL WORKER
EXECUTION" directive.

Item 2 (dependency parity): unlike tests/test_m4d2_live_postgres.py and
tests/test_m4d2_live_fastapi_redis.py (which vendored HEAD of each
package's default branch), this file is run with `PYTHONPATH` pointed at
`/tmp/m4d2b_vendor` -- fastapi/psycopg/redis-py/rq/starlette checked out
at the EXACT git tag matching requirements-production.txt's pin (or, for
starlette, the latest tag satisfying fastapi's own declared
`starlette>=0.40.0,<0.51.0` constraint, since requirements-production.txt
does not pin it directly and pip's resolver would do the same thing
absent a lock file). See PATCH_APPLICATION_REPORT.md's M4D.2b section for
the exact tag/commit table and the one disclosed, unavoidable gap
(pydantic pinned at 2.13.4 requires pydantic-core==2.46.4 exactly, a
compiled Rust/PyO3 extension; building it needs `cargo` to fetch
dependencies from crates.io/index.crates.io, confirmed blocked from this
sandbox by the same egress policy as PyPI/apt/Docker Hub -- the
pre-installed pydantic 2.13.3 + its correctly-paired pydantic-core 2.46.3
is used instead, a real, internally-consistent, already-installed pair,
one patch version behind the pin).

Item 3 (real RQ production-job execution): unlike
tests/test_m4d2_live_fastapi_redis.py's `LiveRedisRQTests` (which
proved real Redis enqueue of the real `execute_modification_job` job,
then deliberately cancelled it and ran dedicated *test* job functions
through `rq.SimpleWorker` instead -- disclosed there and corrected in
STATUS.md by this same M4D.2b pass), this file drives the REAL
`omni_prod.worker_tasks.execute_modification_job` itself through a REAL
`rq.Worker`, in a genuinely separate OS process
(`tests/m4d2b_worker_process.py`, see its own docstring for why that
avoids the fork-after-open-pool hazard). The only substitution is at the
documented, real, already-existing local-model gateway boundary
(`omni_prod.model_runtime_config.ModelRuntimeConfig.from_env()`'s
*local-first* primary route -- see tests/m4d2b_local_model_server.py's
docstring): a real local HTTP server stands in for a real hosted LLM,
because this sandbox has no route to one. Nothing about RQ, Redis,
Postgres, or `execute_modification_job`'s own control flow is mocked or
monkeypatched.

Must run standalone (own process), same reason as
test_m4d2_live_fastapi_redis.py: `python3 -m unittest tests.test_m4d2b_parity_and_worker -v`.
"""
from __future__ import annotations

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
        return f'live-infra dependency not importable ({exc}) -- see PATCH_APPLICATION_REPORT.md M4D.2b section'
    database_url = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')
    redis_url = os.environ.get('M4D2_REDIS_URL', 'redis://127.0.0.1:6379/0')
    try:
        conn = psycopg.connect(database_url, connect_timeout=3)
        conn.close()
    except Exception as exc:  # pragma: no cover - environment probe
        return f'cannot reach live Postgres at {database_url!r}: {exc}'
    try:
        redis.Redis.from_url(redis_url, socket_connect_timeout=3).ping()
    except Exception as exc:  # pragma: no cover - environment probe
        return f'cannot reach live Redis at {redis_url!r}: {exc}'
    if not shutil.which('docker'):
        return 'docker binary not found -- required to reach (and honestly demonstrate) the real sandbox-image blocker'
    if 'omni_prod.investor_app' in sys.modules:
        return ('omni_prod.investor_app was already imported by another test module in this '
                'process -- run this file standalone: python3 -m unittest tests.test_m4d2b_parity_and_worker')
    return None


_SKIP = _skip_reason()

DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')
REDIS_URL = os.environ.get('M4D2_REDIS_URL', 'redis://127.0.0.1:6379/0')
_BILLING_ADMIN_KEY = 'm4d2b-live-billing-admin-key'
_ARTIFACT_ROOT = tempfile.mkdtemp(prefix='m4d2b_worker_artifacts_')
_MODEL_SERVER_PORT = int(os.environ.get('M4D2B_MODEL_SERVER_PORT', '8098'))
_MODEL_SERVER_URL = f'http://127.0.0.1:{_MODEL_SERVER_PORT}/v1'

if _SKIP is None:
    os.environ['OMNI_CREATOR_PERSISTENCE'] = 'postgres'
    os.environ['OMNI_DATABASE_URL'] = DATABASE_URL
    os.environ['OMNI_REDIS_URL'] = REDIS_URL
    os.environ['OMNI_BILLING_ADMIN_KEY'] = _BILLING_ADMIN_KEY
    os.environ.setdefault('OMNI_SECRET_KEY', 'm4d2b-live-worker-secret-' + 'x' * 32)
    os.environ['OMNI_ENABLE_LIVE_BUILD'] = '1'
    os.environ['OMNI_LOCAL_MODEL_URL'] = _MODEL_SERVER_URL
    os.environ['M4D2B_ARTIFACT_ROOT'] = _ARTIFACT_ROOT

    from fastapi.testclient import TestClient

    import omni_prod.investor_app as iapp
    from omni_prod.workspace import PostgresProjectWorkspace
    from tests.test_m4d2_live_postgres import DiskArtifactStore
    from tests.m4d2b_local_model_server import LocalModelServer

    assert iapp._v28_pool is not None, 'OMNI_CREATOR_PERSISTENCE=postgres must have wired a real DatabasePool'
    iapp._v28.engine.workspace = PostgresProjectWorkspace(iapp._v28_pool, DiskArtifactStore(_ARTIFACT_ROOT))


_WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), 'm4d2b_worker_process.py')
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_separate_worker_process(timeout: float = 60.0) -> subprocess.CompletedProcess:
    """Spawns tests/m4d2b_worker_process.py as a genuinely separate OS
    process (not the test process, not a thread) with the environment it
    needs, and waits for it to drain the queue in burst mode."""
    env = os.environ.copy()
    existing = os.environ.get('PYTHONPATH', '')
    env['PYTHONPATH'] = (_REPO_ROOT + os.pathsep + existing) if existing else _REPO_ROOT
    proc = subprocess.run(
        [sys.executable, _WORKER_SCRIPT, '15'],
        cwd=_REPO_ROOT, env=env, capture_output=True, text=True, timeout=timeout,
    )
    return proc


@unittest.skipIf(_SKIP, _SKIP)
class RealWorkerExecutionTests(unittest.TestCase):
    """Directive item 3, required proofs 1-9: the REAL production
    `execute_modification_job` dequeued and executed by a REAL `rq.Worker`
    in a genuinely separate OS process
    (REAL_RQ_SEPARATE_PROCESS_WORKER_VERIFIED -- stronger than, and
    explicitly not claimed equivalent to, M4D.2's in-process
    `rq.SimpleWorker` proof, per the directive's own distinction)."""

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
        email = f'm4d2b-{uuid.uuid4().hex[:12]}@example.com'
        r = self.client.post('/api/v28/auth/register', json={'email': email, 'password': 'StrongPass123!'})
        self.assertEqual(r.status_code, 200, r.text)
        reg = r.json()
        up = self.client.post('/api/v28/admin/subscription',
                               headers={'X-148AI-Billing-Admin-Key': _BILLING_ADMIN_KEY},
                               json={'user_id': reg['user']['id'], 'plan': 'business'})
        self.assertEqual(up.status_code, 200, up.text)
        return reg

    def _create_project_with_seed_version(self, reg: dict, *, acceptance_id: str = 'A1') -> tuple[str, str, str]:
        h = {'Authorization': 'Bearer ' + reg['token']}
        pr = self.client.post('/api/v28/projects', headers=h, json={'title': 'M4D.2b real worker project'})
        self.assertEqual(pr.status_code, 200, pr.text)
        project_id = pr.json()['id']

        from omni_prod.product_spec import ProductSpec
        from omni_prod.spec_repository import PostgresSpecRepository
        _, key = iapp._v28.resolve_project_key(token=reg['token'], project_id=project_id)
        spec = ProductSpec.from_dict({
            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
            'requirements': [{'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True}],
            'acceptance': [{'id': acceptance_id, 'requirement_id': 'R1', 'text': 'home shows todo list'}],
        })
        import json as _json
        manifest = _json.dumps({
            'build': [],
            'verify': [{'name': 'acceptance', 'argv': ['python3', '-m', 'pytest', '-q'],
                        'acceptance_ids': [acceptance_id]}],
        })
        version = iapp._v28.engine.workspace.commit(
            project_id=key, repository={'index.html': '<h1>seed</h1>', '.omni/project.json': manifest},
            message='m4d2b seed', expected_current_version_id=None)
        PostgresSpecRepository(iapp._v28_pool).save(version_id=version.id, project_id=key, spec=spec)
        return project_id, version.id, key

    def test_real_worker_process_dequeues_and_executes_execute_modification_job_ambiguous_path(self):
        """REAL_RQ_SEPARATE_PROCESS_WORKER_VERIFIED. Proofs 1-7: real HTTP
        enqueue of the real job -> a real, separate `rq.Worker` OS process
        dequeues that SAME job (same modification_id / job id) -> the real
        `execute_modification_job` function actually runs, resolves its
        real dependencies (Postgres repos, workspace, the real
        `_modification_components()` gateway wiring), calls the real
        `ChangeClassifierAgent.classify()` over real HTTP to the
        deterministic local model server -> transitions the real
        ModificationRequest QUEUED -> RUNNING -> NEEDS_CLARIFICATION ->
        Postgres holds the durable result, independently verified both via
        the real HTTP status route and directly via the repository."""
        reg = self._register_and_upgrade()
        h = {'Authorization': 'Bearer ' + reg['token']}
        project_id, version_id, key = self._create_project_with_seed_version(reg, acceptance_id='A1')

        from omni_prod.queueing import BUILD_QUEUE
        import rq
        q = rq.Queue(BUILD_QUEUE, connection=self.redis_conn)

        propose = self.client.post(
            f'/api/v28/projects/{project_id}/versions/{version_id}/modifications', headers=h,
            json={'followup': 'not sure what to build -- M4D2B_CLASSIFY:ambiguous please clarify the request'})
        self.assertEqual(propose.status_code, 202, propose.text)
        body = propose.json()
        self.assertEqual(body['dispatch'], 'enqueued')
        modification_id = body['modification_id']

        job = q.fetch_job(modification_id)
        self.assertIsNotNone(job, 'the real production enqueue must have created this real rq job')
        self.assertEqual(job.func_name, 'omni_prod.worker_tasks.execute_modification_job')
        self.assertEqual(job.args, (modification_id,))
        self.assertFalse(job.is_finished)

        proc = _run_separate_worker_process()
        self.assertEqual(proc.returncode, 0,
                          f'separate worker process failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
        self.assertIn('M4D2B_WORKER_PROCESS_DONE ran=True', proc.stdout, proc.stdout + proc.stderr)

        job.refresh()
        self.assertTrue(job.is_finished, f'job status after the separate worker ran: {job.get_status()}; '
                                          f'worker stderr:\n{proc.stderr}')

        status = self.client.get(f'/api/v28/projects/{project_id}/modifications/{modification_id}', headers=h)
        self.assertEqual(status.status_code, 200, status.text)
        d = status.json()
        self.assertEqual(d['status'], 'NEEDS_CLARIFICATION', d)
        self.assertEqual(d['classification'], 'ambiguous', d)
        self.assertIsNone(d['promoted_version_id'])
        self.assertIsNotNone(d['completed_at'])

        from omni_prod.modification_repository import PostgresModificationRepository
        details = PostgresModificationRepository(iapp._v28_pool).get_details(modification_id, key)
        self.assertEqual(details.status, 'NEEDS_CLARIFICATION')
        self.assertEqual(details.classification, 'ambiguous')
        self.assertFalse(details.billable)

    def test_real_worker_process_system_bug_path_hits_real_sandbox_docker_image_blocker(self):
        """Proof 9 (a controlled worker failure is recorded correctly and
        leaves recoverable durable state), using a REAL failure rather than
        a synthetic one: the real classify() -> real repair-loop ->
        real `SandboxRepositoryExecutor.execute()` -> a real
        `docker run omni-sandbox:latest ...` subprocess, which genuinely
        fails in this sandbox. The specific real failure observed is a
        previously-unknown Docker-CLI-version incompatibility in
        `omni_prod/sandbox.py`'s `--mount ...,rw` flag syntax against this
        sandbox's Docker 29.4.3 (`invalid field 'rw' must be a key=value
        pair`) -- a different real docker error than the also-genuine,
        already-disclosed image-pull-forbidden block (Docker Hub), but
        equally real and equally unmodified; which one surfaces first does
        not change what this test proves. `sandbox.py` is out of M4D.2b's
        scope (M2-era code, unrelated to M4's accept/reject/rollback
        pipeline) and is deliberately left unfixed -- see
        PATCH_APPLICATION_REPORT.md's M4D.2b section, which documents this
        finding for whoever owns that module next. This is not an
        exception the worker crashes on: `run_sandbox()` captures the
        nonzero returncode into a normal `ExecutionReport(passed=False)`,
        so the real, intended business outcome is a completed `FAILED`
        modification with the real docker error text preserved in
        `evidence_json`, not a `worker_exception`. The repair loop runs
        the full real `max_repair_rounds=3` (each round: a real repair()
        call to the local model server, a real docker attempt, a real
        failure) before giving up, exactly as `run_free_repair` would for
        a real LLM that failed to produce a working fix."""
        reg = self._register_and_upgrade()
        h = {'Authorization': 'Bearer ' + reg['token']}
        project_id, version_id, key = self._create_project_with_seed_version(reg, acceptance_id='A1')

        propose = self.client.post(
            f'/api/v28/projects/{project_id}/versions/{version_id}/modifications', headers=h,
            json={'followup': 'fix the todo list -- M4D2B_CLASSIFY:system_bug M4D2B_IDS:A1 per acceptance A1'})
        self.assertEqual(propose.status_code, 202, propose.text)
        modification_id = propose.json()['modification_id']
        self.assertEqual(propose.json()['dispatch'], 'enqueued')

        proc = _run_separate_worker_process()
        self.assertEqual(proc.returncode, 0,
                          f'separate worker process failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
        self.assertIn('M4D2B_WORKER_PROCESS_DONE ran=True', proc.stdout, proc.stdout + proc.stderr)

        status = self.client.get(f'/api/v28/projects/{project_id}/modifications/{modification_id}', headers=h)
        self.assertEqual(status.status_code, 200, status.text)
        d = status.json()
        self.assertEqual(d['status'], 'FAILED', d)
        self.assertEqual(d['classification'], 'system_bug', d)
        # error_code is GateResult.blocking_gate ('verification'), not the
        # 'verification_failed' fallback string -- that fallback is used
        # only when outcome.gates is None, which never happens on this
        # (non-ambiguous) path; see _run_modification_job in worker_tasks.py.
        self.assertEqual(d['error_code'], 'verification', d)
        self.assertEqual(d['repair_rounds'], 3, d)
        evidence = d['evidence']
        self.assertFalse(evidence['billing'] == 'settled', 'system_bug is never billable -- must be released, not settled')
        self.assertEqual(evidence['billing'], 'released')
        build_log = evidence['verification']['build_log_tail']
        self.assertTrue(
            ('Unable to find image' in build_log) or ('Forbidden' in build_log)
            or ('docker run' in build_log) or ('--mount' in build_log),
            f'expected a REAL docker error to be present in the persisted build log, got: {build_log!r}')

        # Recoverable durable state: no promotion happened, current() is
        # still the seed version, and the modification remains normally
        # gettable (not stuck / not corrupting the project).
        current = iapp._v28.engine.workspace.current(key)
        self.assertEqual(current.id, version_id, 'a FAILED modification must never advance current()')
        still_gettable = self.client.get(f'/api/v28/projects/{project_id}/modifications/{modification_id}', headers=h)
        self.assertEqual(still_gettable.status_code, 200)

    def test_duplicate_delivery_of_the_same_modification_does_not_reexecute_or_duplicate_state(self):
        """Proof 8: retry/double-delivery of the same job does not create
        duplicate promotion/candidate state. Drives the real ambiguous
        path to completion once via the real worker, then simulates a
        second, independent RQ delivery of the SAME production function
        for the SAME modification_id (a different rq job id, since a
        duplicate delivery is two distinct queue messages that both name
        the same modification -- not the same Redis job key) through a
        second real, separate worker process run. `_run_modification_job`'s
        own `jobs.transition_running(modification_id)` guard must make the
        second execution a real no-op (it returns None without touching
        state) because the request is already terminal."""
        reg = self._register_and_upgrade()
        h = {'Authorization': 'Bearer ' + reg['token']}
        project_id, version_id, key = self._create_project_with_seed_version(reg, acceptance_id='A1')

        propose = self.client.post(
            f'/api/v28/projects/{project_id}/versions/{version_id}/modifications', headers=h,
            json={'followup': 'duplicate delivery check -- M4D2B_CLASSIFY:ambiguous please clarify'})
        modification_id = propose.json()['modification_id']

        first_run = _run_separate_worker_process()
        self.assertEqual(first_run.returncode, 0, first_run.stdout + first_run.stderr)
        before = self.client.get(f'/api/v28/projects/{project_id}/modifications/{modification_id}', headers=h).json()
        self.assertEqual(before['status'], 'NEEDS_CLARIFICATION')
        completed_at_1 = before['completed_at']

        from omni_prod.queueing import enqueue_build, BUILD_QUEUE
        enqueue_build(REDIS_URL, 'omni_prod.worker_tasks.execute_modification_job', modification_id,
                       job_id=f'm4d2b_dup_{uuid.uuid4().hex}', queue_name=BUILD_QUEUE)

        second_run = _run_separate_worker_process()
        self.assertEqual(second_run.returncode, 0, second_run.stdout + second_run.stderr)
        self.assertIn('M4D2B_WORKER_PROCESS_DONE ran=True', second_run.stdout)

        after = self.client.get(f'/api/v28/projects/{project_id}/modifications/{modification_id}', headers=h).json()
        self.assertEqual(after['status'], 'NEEDS_CLARIFICATION')
        self.assertEqual(after['completed_at'], completed_at_1,
                          'a duplicate delivery must never re-run the job body or overwrite the terminal result')

        current = iapp._v28.engine.workspace.current(key)
        self.assertEqual(current.id, version_id, 'duplicate delivery must never promote/duplicate a version')


if __name__ == '__main__':
    unittest.main()
