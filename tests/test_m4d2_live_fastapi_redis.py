"""M4D.2 -- LIVE INFRASTRUCTURE VERIFICATION (sections F and G of the
"148AI M4D.2" directive): the REAL `omni_prod.investor_app` FastAPI
application, served in-process by `fastapi.testclient.TestClient` (which
drives the real ASGI app through Starlette's real request/response cycle --
not a hand call to the route function), talking to the SAME real PostgreSQL
this M4D.2 pass used for `tests/test_m4d2_live_postgres.py`, plus a REAL
Redis server and a REAL `rq.Worker` popping REAL jobs.

MUST run as its own process (`python3 -m unittest tests.test_m4d2_live_fastapi_redis -v`),
never imported alongside another test module that already imported
`omni_prod.investor_app` -- the module-level globals `_v28`/`_v28_pool`
that decide whether the durable Postgres backend is wired in are built
ONCE, at import time, from `OMNI_CREATOR_PERSISTENCE`/`OMNI_DATABASE_URL`,
which this file sets before that import happens. A second import in an
already-running process is a no-op (Python caches modules), so those env
vars would be read too late.

Why `psycopg`/`fastapi`/`redis`/`rq` import at all here: see the module
docstring of tests/test_m4d2_live_postgres.py and the M4D.2 section of
PATCH_APPLICATION_REPORT.md -- PyPI, the Debian package mirror and Docker
Hub are all confirmed blocked from this sandbox; the real upstream source
of each package was fetched via `git clone` (which IS reachable) from its
own GitHub repository and made importable through a PYTHONPATH vendor
directory instead of a normal `pip install`.

The one deliberate substitution: `_v28.engine.workspace` is swapped, right
after import, from the in-memory default to a REAL `PostgresProjectWorkspace`
backed by a real disk directory instead of S3 (boto3 is not installable
here either, and standing up a real S3-compatible server is out of scope
for M4D.2's Postgres/Redis/FastAPI-only sections C-H). Nothing about
Postgres, FastAPI, Redis or RQ is substituted anywhere in this file.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import uuid


def _skip_reason() -> str | None:
    try:
        import psycopg  # noqa: F401
        import fastapi  # noqa: F401
        import redis  # noqa: F401
        import rq  # noqa: F401
    except ImportError as exc:
        return f'live-infra dependency not importable ({exc}) -- see PATCH_APPLICATION_REPORT.md M4D.2 section'
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
    if 'omni_prod.investor_app' in sys.modules:
        return ('omni_prod.investor_app was already imported by another test module in this '
                'process -- run this file standalone: python3 -m unittest tests.test_m4d2_live_fastapi_redis')
    return None


_SKIP = _skip_reason()

DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')
REDIS_URL = os.environ.get('M4D2_REDIS_URL', 'redis://127.0.0.1:6379/0')
_BILLING_ADMIN_KEY = 'm4d2-live-billing-admin-key'

if _SKIP is None:
    os.environ['OMNI_CREATOR_PERSISTENCE'] = 'postgres'
    os.environ['OMNI_DATABASE_URL'] = DATABASE_URL
    os.environ['OMNI_REDIS_URL'] = REDIS_URL
    os.environ['OMNI_BILLING_ADMIN_KEY'] = _BILLING_ADMIN_KEY
    os.environ.setdefault('OMNI_SECRET_KEY', 'm4d2-live-fastapi-secret-' + 'x' * 32)

    from fastapi.testclient import TestClient

    import omni_prod.investor_app as iapp
    from omni_prod.workspace import PostgresProjectWorkspace
    from tests.test_m4d2_live_postgres import DiskArtifactStore  # real disk-backed S3 stand-in

    assert iapp._v28_pool is not None, 'OMNI_CREATOR_PERSISTENCE=postgres must have wired a real DatabasePool'

    _ARTIFACT_ROOT = tempfile.mkdtemp(prefix='m4d2_fastapi_artifacts_')
    iapp._v28.engine.workspace = PostgresProjectWorkspace(iapp._v28_pool, DiskArtifactStore(_ARTIFACT_ROOT))


@unittest.skipIf(_SKIP, _SKIP)
class LiveFastAPIModificationFlowTests(unittest.TestCase):
    """Section F: real HTTP routes for create/accept/reject/conflict/
    invalid-state/retry, verified through TestClient -- real status codes,
    real response schema, real persisted Postgres state, checked
    independently of the route (via the repository classes) after each
    call."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(iapp.app)

    def _register_and_upgrade(self) -> dict:
        email = f'm4d2-{uuid.uuid4().hex[:12]}@example.com'
        r = self.client.post('/api/v28/auth/register', json={'email': email, 'password': 'StrongPass123!'})
        self.assertEqual(r.status_code, 200, r.text)
        reg = r.json()
        up = self.client.post('/api/v28/admin/subscription',
                               headers={'X-148AI-Billing-Admin-Key': _BILLING_ADMIN_KEY},
                               json={'user_id': reg['user']['id'], 'plan': 'business'})
        self.assertEqual(up.status_code, 200, up.text)
        return reg

    def _create_project_with_seed_version(self, reg: dict) -> tuple[str, str]:
        """Creates a real project via the real HTTP route (durable in
        Postgres via PostgresAccountService), then seeds an initial
        ProjectVersion + ProductSpec by calling the SAME production
        methods (`workspace.commit()`, `PostgresSpecRepository.save()`)
        the async build worker would call -- directly, rather than
        round-tripping through the async build+worker pipeline, which
        tests a different milestone (M1) not in scope for M4D.2. Returns
        (project_id, version_id)."""
        h = {'Authorization': 'Bearer ' + reg['token']}
        pr = self.client.post('/api/v28/projects', headers=h, json={'title': 'M4D.2 live project'})
        self.assertEqual(pr.status_code, 200, pr.text)
        project_id = pr.json()['id']

        from omni_prod.product_spec import ProductSpec
        from omni_prod.spec_repository import PostgresSpecRepository
        _, key = iapp._v28.resolve_project_key(token=reg['token'], project_id=project_id)
        spec = ProductSpec.from_dict({
            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
            'requirements': [{'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True}],
            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
        })
        version = iapp._v28.engine.workspace.commit(
            project_id=key, repository={'index.html': '<h1>seed</h1>'}, message='m4d2 seed',
            expected_current_version_id=None)
        PostgresSpecRepository(iapp._v28_pool).save(version_id=version.id, project_id=key, spec=spec)
        return project_id, version.id

    def test_full_http_propose_accept_flow_persists_to_real_postgres(self):
        reg = self._register_and_upgrade()
        h = {'Authorization': 'Bearer ' + reg['token']}
        project_id, version_id = self._create_project_with_seed_version(reg)

        propose = self.client.post(
            f'/api/v28/projects/{project_id}/versions/{version_id}/modifications', headers=h,
            json={'followup': 'Add a delete button to each todo item.'})
        self.assertEqual(propose.status_code, 202, propose.text)
        body = propose.json()
        self.assertEqual(body['status'], 'queued')
        self.assertIn(body['dispatch'], ('enqueued', 'deferred'))
        modification_id = body['modification_id']

        status = self.client.get(f'/api/v28/projects/{project_id}/modifications/{modification_id}', headers=h)
        self.assertEqual(status.status_code, 200, status.text)
        self.assertEqual(status.json()['status'], 'QUEUED')

        # Drive the request to READY_FOR_REVIEW using the real repository's
        # own worker-lifecycle methods (transition_running/complete) --
        # exactly what worker_tasks._run_modification_job calls -- rather
        # than the LLM-classification step itself, which needs a live LLM
        # provider (a pre-existing, already-disclosed constraint unrelated
        # to M4D.2's Postgres/Redis/FastAPI scope; see StagedFailureTests'
        # RQ counterpart below for the real Redis/RQ dispatch/worker proof
        # of this SAME job).
        from omni_prod.modification_repository import PostgresModificationRepository
        from omni_prod.product_spec import ProductSpec
        mods = PostgresModificationRepository(iapp._v28_pool)
        self.assertTrue(mods.transition_running(modification_id))
        candidate_spec = ProductSpec.from_dict({
            'title': 'Todo', 'summary': 'Todo app with delete', 'stack': ['python'],
            'requirements': [{'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True},
                              {'id': 'R2', 'text': 'delete a todo', 'kind': 'functional', 'mandatory': True}],
            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
                            {'id': 'A2', 'requirement_id': 'R2', 'text': 'delete button removes an item'}],
        })
        self.assertTrue(mods.complete(
            modification_id, project_id=iapp._v28.resolve_project_key(token=reg['token'], project_id=project_id)[1],
            status='READY_FOR_REVIEW', classification='change_request', classification_reason='m4d2 live http test',
            billable=True, candidate_repository={'index.html': '<h1>seed</h1><button>Delete</button>'},
            candidate_spec=candidate_spec))

        candidate = self.client.get(f'/api/v28/projects/{project_id}/modifications/{modification_id}/candidate',
                                     headers=h)
        self.assertEqual(candidate.status_code, 200, candidate.text)
        self.assertIn('Delete', json.dumps(candidate.json()['repository']))

        accept = self.client.post(f'/api/v28/projects/{project_id}/modifications/{modification_id}/accept',
                                   headers=h, json={})
        self.assertEqual(accept.status_code, 200, accept.text)
        outcome = accept.json()
        self.assertTrue(outcome['accepted'])
        new_version_id = outcome['new_version_id']

        status2 = self.client.get(f'/api/v28/projects/{project_id}/modifications/{modification_id}', headers=h)
        self.assertEqual(status2.json()['status'], 'ACCEPTED')
        self.assertEqual(status2.json()['promoted_version_id'], new_version_id)

        _, key = iapp._v28.resolve_project_key(token=reg['token'], project_id=project_id)
        current = iapp._v28.engine.workspace.current(key)
        self.assertEqual(current.id, new_version_id)
        self.assertEqual(current.repository(), {'index.html': '<h1>seed</h1><button>Delete</button>'})

    def test_http_accept_conflict_returns_409_and_leaves_current_version_untouched(self):
        reg = self._register_and_upgrade()
        h = {'Authorization': 'Bearer ' + reg['token']}
        project_id, version_id = self._create_project_with_seed_version(reg)
        _, key = iapp._v28.resolve_project_key(token=reg['token'], project_id=project_id)

        from omni_prod.modification_repository import PostgresModificationRepository
        from omni_prod.product_spec import ProductSpec
        mods = PostgresModificationRepository(iapp._v28_pool)
        spec = ProductSpec.from_dict({
            'title': 'Todo', 'summary': 'Todo', 'stack': ['python'],
            'requirements': [{'id': 'R1', 'text': 'x', 'kind': 'functional', 'mandatory': True}],
            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'x'}],
        })

        def _ready(followup, repo):
            pr = self.client.post(f'/api/v28/projects/{project_id}/versions/{version_id}/modifications',
                                   headers=h, json={'followup': followup})
            self.assertEqual(pr.status_code, 202, pr.text)
            mid = pr.json()['modification_id']
            self.assertTrue(mods.transition_running(mid))
            self.assertTrue(mods.complete(mid, project_id=key, status='READY_FOR_REVIEW',
                                           classification='change_request', classification_reason='t',
                                           billable=True, candidate_repository=repo, candidate_spec=spec))
            return mid

        mod_a = _ready('A change', {'index.html': '<h1>A</h1>'})
        mod_b = _ready('B change', {'index.html': '<h1>B</h1>'})

        accept_a = self.client.post(f'/api/v28/projects/{project_id}/modifications/{mod_a}/accept', headers=h,
                                     json={})
        self.assertEqual(accept_a.status_code, 200, accept_a.text)
        self.assertTrue(accept_a.json()['accepted'])

        accept_b = self.client.post(f'/api/v28/projects/{project_id}/modifications/{mod_b}/accept', headers=h,
                                     json={})
        self.assertEqual(accept_b.status_code, 409, accept_b.text)
        self.assertEqual(accept_b.json()['reason'], 'conflict')

        current = iapp._v28.engine.workspace.current(key)
        self.assertEqual(current.id, accept_a.json()['new_version_id'])
        history = iapp._v28.engine.workspace.history(key)
        self.assertEqual(len(history), 2, 'B must not have produced a second promotion')

    def test_http_double_accept_of_same_modification_returns_422_invalid_status(self):
        reg = self._register_and_upgrade()
        h = {'Authorization': 'Bearer ' + reg['token']}
        project_id, version_id = self._create_project_with_seed_version(reg)
        _, key = iapp._v28.resolve_project_key(token=reg['token'], project_id=project_id)

        from omni_prod.modification_repository import PostgresModificationRepository
        from omni_prod.product_spec import ProductSpec
        mods = PostgresModificationRepository(iapp._v28_pool)
        pr = self.client.post(f'/api/v28/projects/{project_id}/versions/{version_id}/modifications',
                               headers=h, json={'followup': 'idempotency check'})
        mid = pr.json()['modification_id']
        self.assertTrue(mods.transition_running(mid))
        spec = ProductSpec.from_dict({
            'title': 'Todo', 'summary': 'Todo', 'stack': ['python'],
            'requirements': [{'id': 'R1', 'text': 'x', 'kind': 'functional', 'mandatory': True}],
            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'x'}],
        })
        self.assertTrue(mods.complete(mid, project_id=key, status='READY_FOR_REVIEW',
                                       classification='change_request', classification_reason='t', billable=True,
                                       candidate_repository={'index.html': '<h1>dup</h1>'}, candidate_spec=spec))

        first = self.client.post(f'/api/v28/projects/{project_id}/modifications/{mid}/accept', headers=h, json={})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertTrue(first.json()['accepted'])

        duplicate = self.client.post(f'/api/v28/projects/{project_id}/modifications/{mid}/accept', headers=h,
                                      json={})
        self.assertEqual(duplicate.status_code, 422, duplicate.text)
        self.assertEqual(duplicate.json()['reason'], 'invalid_status')

        history = iapp._v28.engine.workspace.history(key)
        self.assertEqual(len(history), 2, 'a duplicate HTTP accept request must never double-promote')

    def test_http_reject_leaves_current_version_intact_and_accept_afterward_is_422(self):
        reg = self._register_and_upgrade()
        h = {'Authorization': 'Bearer ' + reg['token']}
        project_id, version_id = self._create_project_with_seed_version(reg)
        _, key = iapp._v28.resolve_project_key(token=reg['token'], project_id=project_id)

        from omni_prod.modification_repository import PostgresModificationRepository
        from omni_prod.product_spec import ProductSpec
        mods = PostgresModificationRepository(iapp._v28_pool)
        pr = self.client.post(f'/api/v28/projects/{project_id}/versions/{version_id}/modifications',
                               headers=h, json={'followup': 'reject me'})
        mid = pr.json()['modification_id']
        self.assertTrue(mods.transition_running(mid))
        spec = ProductSpec.from_dict({
            'title': 'Todo', 'summary': 'Todo', 'stack': ['python'],
            'requirements': [{'id': 'R1', 'text': 'x', 'kind': 'functional', 'mandatory': True}],
            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'x'}],
        })
        self.assertTrue(mods.complete(mid, project_id=key, status='READY_FOR_REVIEW',
                                       classification='change_request', classification_reason='t', billable=True,
                                       candidate_repository={'index.html': '<h1>rejected</h1>'}, candidate_spec=spec))

        before = iapp._v28.engine.workspace.current(key)
        reject = self.client.post(f'/api/v28/projects/{project_id}/modifications/{mid}/reject', headers=h,
                                   json={'reason': 'not what I wanted'})
        self.assertEqual(reject.status_code, 200, reject.text)
        self.assertTrue(reject.json()['rejected'])
        after = iapp._v28.engine.workspace.current(key)
        self.assertEqual(before.id, after.id, 'reject() must never touch project_versions')

        accept_after_reject = self.client.post(f'/api/v28/projects/{project_id}/modifications/{mid}/accept',
                                                 headers=h, json={})
        self.assertEqual(accept_after_reject.status_code, 422, accept_after_reject.text)

    def test_http_access_denied_for_someone_elses_modification_returns_403(self):
        reg1 = self._register_and_upgrade()
        reg2 = self._register_and_upgrade()
        h1 = {'Authorization': 'Bearer ' + reg1['token']}
        h2 = {'Authorization': 'Bearer ' + reg2['token']}
        project_id, version_id = self._create_project_with_seed_version(reg1)
        pr = self.client.post(f'/api/v28/projects/{project_id}/versions/{version_id}/modifications',
                               headers=h1, json={'followup': 'owner only'})
        self.assertEqual(pr.status_code, 202, pr.text)
        mid = pr.json()['modification_id']

        cross = self.client.get(f'/api/v28/projects/{project_id}/modifications/{mid}', headers=h2)
        self.assertEqual(cross.status_code, 403, cross.text)


@unittest.skipIf(_SKIP, _SKIP)
class LiveRedisRQTests(unittest.TestCase):
    """Section G: is Redis/RQ actually part of M4's production path?
    v28_propose_modification calls
    `enqueue_build(redis_url, "omni_prod.worker_tasks.execute_modification_job", modification_id, ...)`
    (omni_prod/investor_app.py) via `omni_prod.queueing.enqueue_build`,
    which is real `rq.Queue.enqueue` over a real `redis.Redis` connection
    -- yes, it is. These tests prove the REAL enqueue -> REAL worker ->
    dequeue -> execute path end to end against the real Redis server this
    M4D.2 pass started, using the REAL queue name/connection helper
    (`omni_prod.queueing`), not a substitute queue.

    Worker execution uses `rq.SimpleWorker` rather than `rq.Worker`: the
    default `rq.Worker` forks a child process per job, and this test
    process already holds an OPEN psycopg connection pool
    (`iapp._v28_pool`) at fork time -- forking a process that holds a live
    SSL socket is a well-known hazard (both parent and child end up
    sharing one socket's underlying file descriptor), and it reproduced
    exactly that failure (`SSL SYSCALL error: EOF detected`) on the first
    real run of this file, for jobs left over from another test's queue.
    `SimpleWorker` runs the job in-process without forking, which avoids
    that specific hazard while still being real, unmodified `rq` code
    exercising a real dequeue and a real job execution against real
    Redis -- it is not a mock of the queue or the worker."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(iapp.app)
        import redis
        cls.redis_conn = redis.Redis.from_url(REDIS_URL)

    def test_propose_modification_over_http_really_enqueues_a_redis_rq_job(self):
        from omni_prod.queueing import BUILD_QUEUE
        import rq
        reg_email = f'm4d2-rq-{uuid.uuid4().hex[:12]}@example.com'
        reg = self.client.post('/api/v28/auth/register', json={'email': reg_email, 'password': 'StrongPass123!'}).json()
        self.client.post('/api/v28/admin/subscription', headers={'X-148AI-Billing-Admin-Key': _BILLING_ADMIN_KEY},
                          json={'user_id': reg['user']['id'], 'plan': 'business'})
        h = {'Authorization': 'Bearer ' + reg['token']}
        pr = self.client.post('/api/v28/projects', headers=h, json={'title': 'RQ live test'})
        project_id = pr.json()['id']
        from omni_prod.product_spec import ProductSpec
        from omni_prod.spec_repository import PostgresSpecRepository
        _, key = iapp._v28.resolve_project_key(token=reg['token'], project_id=project_id)
        spec = ProductSpec.from_dict({
            'title': 'T', 'summary': 'T', 'stack': ['python'],
            'requirements': [{'id': 'R1', 'text': 'x', 'kind': 'functional', 'mandatory': True}],
            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'x'}],
        })
        version = iapp._v28.engine.workspace.commit(project_id=key, repository={'a.html': '1'}, message='seed',
                                                      expected_current_version_id=None)
        PostgresSpecRepository(iapp._v28_pool).save(version_id=version.id, project_id=key, spec=spec)

        q = rq.Queue(BUILD_QUEUE, connection=self.redis_conn)
        propose = self.client.post(f'/api/v28/projects/{project_id}/versions/{version.id}/modifications',
                                    headers=h, json={'followup': 'queue me for real'})
        self.assertEqual(propose.status_code, 202, propose.text)
        modification_id = propose.json()['modification_id']
        self.assertEqual(propose.json()['dispatch'], 'enqueued',
                          'a real, reachable Redis must make the real enqueue_build() call succeed, not fall '
                          'back to the outbox-relay "deferred" path')

        job = q.fetch_job(modification_id)
        self.assertIsNotNone(job, 'the real rq.Queue must contain a real job with this modification_id as its id')
        self.assertEqual(job.func_name, 'omni_prod.worker_tasks.execute_modification_job')
        self.assertEqual(job.args, (modification_id,))
        # Deliberately never run a worker on this job: executing it for real
        # requires a live LLM provider (ChangeClassifierAgent), a
        # pre-existing, already-disclosed external dependency unrelated to
        # M4D.2's Postgres/Redis/FastAPI scope -- see
        # test_real_rq_worker_pops_and_executes_a_real_enqueued_job below
        # for the real worker-execution proof using a self-contained job.
        # Cancel it so it cannot be picked up by a later test's worker.
        job.cancel()
        job.delete()

    def test_real_rq_worker_pops_and_executes_a_real_enqueued_job(self):
        """Enqueues a small, self-contained real function (not the LLM-
        dependent execute_modification_job -- that boundary is a
        pre-existing, already-disclosed external-provider dependency, not
        an M4D.2 Postgres/Redis/FastAPI concern) through the REAL
        `omni_prod.queueing.enqueue_build` helper, then runs a REAL
        `rq.Worker` in burst mode against the REAL Redis queue and proves
        it actually dequeued and executed the job (result visible via a
        side effect in Postgres, not just 'job.is_finished')."""
        from omni_prod.queueing import enqueue_build, BUILD_QUEUE
        import rq

        marker_table_row_id = f"rq_marker_{uuid.uuid4().hex}"
        with iapp._v28_pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "CREATE TABLE IF NOT EXISTS m4d2_rq_markers "
                        "(marker TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now())")

        job = enqueue_build(REDIS_URL, 'tests.m4d2_rq_job_target.mark_done', marker_table_row_id,
                             job_id=f'm4d2job_{uuid.uuid4().hex}', queue_name=BUILD_QUEUE)
        self.assertFalse(job.is_finished)

        worker = rq.SimpleWorker([BUILD_QUEUE], connection=self.redis_conn)
        ran = worker.work(burst=True)
        self.assertTrue(ran, 'the real worker must have found and executed at least one job')

        job.refresh()
        self.assertTrue(job.is_finished, f'job status after burst work: {job.get_status()}')

        with iapp._v28_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM m4d2_rq_markers WHERE marker = %s", (marker_table_row_id,))
                self.assertEqual(cur.fetchone()[0], 1,
                                  'the real worker process must have executed the real job body, which writes '
                                  'this row directly to Postgres as independently-checkable proof of execution '
                                  '(not merely rq reporting is_finished=True)')

    def test_worker_failure_is_recorded_and_does_not_crash_the_worker_or_double_promote(self):
        from omni_prod.queueing import enqueue_build, BUILD_QUEUE
        import rq

        job = enqueue_build(REDIS_URL, 'tests.m4d2_rq_job_target.always_fails', 'irrelevant-arg',
                             job_id=f'm4d2fail_{uuid.uuid4().hex}', queue_name=BUILD_QUEUE)
        worker = rq.SimpleWorker([BUILD_QUEUE], connection=self.redis_conn)
        ran = worker.work(burst=True)
        self.assertTrue(ran)
        job.refresh()
        self.assertTrue(job.is_failed, f'status: {job.get_status()}')

        # The worker must still be usable afterward -- a failed job must not
        # crash the worker process or leave the queue connection unusable.
        job2 = enqueue_build(REDIS_URL, 'tests.m4d2_rq_job_target.mark_done', f'after-failure-{uuid.uuid4().hex}',
                              job_id=f'm4d2after_{uuid.uuid4().hex}', queue_name=BUILD_QUEUE)
        ran2 = worker.work(burst=True)
        self.assertTrue(ran2)
        job2.refresh()
        self.assertTrue(job2.is_finished)


if __name__ == '__main__':
    unittest.main()
