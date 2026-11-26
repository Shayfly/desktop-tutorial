"""A live preview lives a day, not an hour (the owner, 2026-11-26, WAREHOUSE 136 option a: a limit that is not money).

The real PostgresPreviewRepository.create and PreviewAccess.issue with a recording pool (no database here; the pg job
runs tests/test_preview_access.py against a real one): the row's expiry is now + 24 h, and the owner's access link
follows the preview instead of ending 16 hours before it. An expired preview is still started again from the
workspace: the launch route always writes a NEW preview row, and the screen offers the start for EXPIRED."""
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from omni_prod import preview_access as PA
from omni_prod import preview_repository as PR

ROOT = Path(__file__).resolve().parent.parent


class Recording:
    """A psycopg-shaped pool that records each statement and its parameters."""

    def __init__(self):
        self.sql = []
        outer = self

        class Cur:
            rowcount = 1

            def execute(self, sql, params=()):
                outer.sql.append((' '.join(sql.split()), params))

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        class Conn:
            def cursor(self):
                return Cur()

            def transaction(self):
                return self

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        self._conn = Conn()

    def connection(self):
        return self._conn


class APreviewLivesADay(unittest.TestCase):
    def test_the_default_is_a_day_and_the_route_reads_it(self):
        self.assertEqual(PR.DEFAULT_TTL_SECONDS, 24 * 3600)
        source = (ROOT / 'omni_prod' / 'investor_app.py').read_text(encoding='utf-8')
        self.assertIn("_PREVIEW_TTL_SECONDS = int(os.getenv('OMNI_PREVIEW_TTL_SECONDS', str(_PREVIEW_DEFAULT_TTL)))",
                      source)
        self.assertNotIn("os.getenv('OMNI_PREVIEW_TTL_SECONDS', '3600')", source)
        self.assertIn('preview_repo.create(preview_id, key, version_id, ttl_seconds=_PREVIEW_TTL_SECONDS)', source)

    def test_the_row_expires_a_day_after_launch(self):
        pool = Recording()
        PR.PostgresPreviewRepository(pool).create('prv_x', 'k', 'v1', ttl_seconds=PR.DEFAULT_TTL_SECONDS)
        sql, params = pool.sql[0]
        self.assertIn("expires_at) VALUES (%s, %s, %s, 'STARTING', now() + make_interval(secs => %s))", sql)
        self.assertEqual(params[-1], 86_400)

    def test_the_owners_link_never_ends_before_the_preview(self):
        self.assertGreaterEqual(PA.OWNER_TTL, timedelta(seconds=PR.DEFAULT_TTL_SECONDS))
        self.assertGreaterEqual(PA.SHARE_TTL, timedelta(seconds=PR.DEFAULT_TTL_SECONDS))      # 7 days: unchanged
        pool = Recording()
        before = datetime.now(timezone.utc)
        _, expires = PA.PreviewAccess(pool).issue('prv_x', kind='owner', issued_to='usr_1')
        self.assertGreaterEqual(datetime.fromisoformat(expires) - before, timedelta(hours=24) - timedelta(seconds=5))

    def test_an_expired_preview_is_started_again_from_the_workspace(self):
        source = (ROOT / 'omni_prod' / 'investor_app.py').read_text(encoding='utf-8')
        launch = source.split('def _v28_preview_launch(', 1)[1].split('\n@app.', 1)[0]
        self.assertIn('preview_id = f"prv_{uuid.uuid4().hex}"', launch)          # every launch is a new row
        self.assertNotIn('EXPIRED', launch)                                    # nothing refuses an expired version
        js = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
        self.assertIn("['EXPIRED', 'STOPPED', 'FAILED', 'UNAVAILABLE'].includes(p.status)", js)
        router_sql = re.sub(r'\s+', ' ', (ROOT / 'omni_prod' / 'preview_repository.py').read_text(encoding='utf-8'))
        self.assertIn("WHERE id = %s AND status = 'RUNNING' AND expires_at > now()", router_sql)     # past it: closed


class ALaunchReusesTheLivePreview(unittest.TestCase):
    """Review S3 (2026-11-26): a preview now lives a day, so a launch of a version whose preview is still starting or
    running reuses it instead of starting another container. The real launch function, with the database, queue and
    sandbox seams stubbed; the repository's query on a recording pool."""

    def launch(self, live):
        from types import SimpleNamespace
        from unittest import mock
        import omni_prod.investor_app as ia
        calls = {'create': [], 'enqueue': []}

        class Repo:
            def __init__(self, pool):
                pass

            def live_for(self, project_id, version_id):
                return live

            def create(self, *a, **k):
                calls['create'].append(a)
        version = SimpleNamespace(repository=lambda: {})
        with mock.patch.object(ia, '_require_durable_backend', lambda *_: None), \
                mock.patch.object(ia, 'external_preview_url', lambda *_: 'x'), \
                mock.patch.object(ia, '_preview_key', lambda *_: 'k'), \
                mock.patch.object(ia, 'parse_preview_contract', lambda *_: None), \
                mock.patch.object(ia, 'parse_web_saas_acceptance_plan', lambda *_: None), \
                mock.patch.object(ia, 'PostgresPreviewRepository', Repo), \
                mock.patch.object(ia, 'enqueue_build', lambda *a, **k: calls['enqueue'].append(a)), \
                mock.patch.object(ia._v28.engine.workspace, 'get', lambda **_: version):
            response = ia._v28_preview_launch('p', 'v1', None)
        return __import__('json').loads(response.body), calls

    def test_a_running_preview_of_the_same_version_is_reused(self):
        body, calls = self.launch('prv_live')
        self.assertEqual(body, {'status': 'REUSED', 'preview_id': 'prv_live'})
        self.assertEqual(calls, {'create': [], 'enqueue': []})              # no new row, no new container

    def test_with_none_live_a_new_preview_starts(self):
        body, calls = self.launch(None)
        self.assertEqual(body['status'], 'STARTING')
        self.assertEqual((len(calls['create']), len(calls['enqueue'])), (1, 1))

    def test_the_query_reads_only_a_live_preview_of_that_version(self):
        pool = Recording()
        pool._conn.cursor().__class__.fetchone = lambda self: None
        self.assertIsNone(PR.PostgresPreviewRepository(pool).live_for('k', 'v1'))
        sql, params = pool.sql[0]
        self.assertIn("WHERE project_id = %s AND version_id = %s AND status IN ('STARTING', 'RUNNING') "
                      "AND expires_at > now()", sql)
        self.assertEqual(params, ('k', 'v1'))


class TheOwnersLinkFollowsAnOverride(unittest.TestCase):
    def test_a_longer_preview_life_lengthens_the_link(self):
        import importlib
        import os
        from unittest import mock
        try:
            with mock.patch.dict(os.environ, {'OMNI_PREVIEW_TTL_SECONDS': str(48 * 3600)}):
                self.assertEqual(importlib.reload(PA).OWNER_TTL, timedelta(hours=48))
            with mock.patch.dict(os.environ, {'OMNI_PREVIEW_TTL_SECONDS': 'a day'}):
                with self.assertRaises(ValueError):
                    importlib.reload(PA)
        finally:
            importlib.reload(PA)


if __name__ == '__main__':
    unittest.main()
