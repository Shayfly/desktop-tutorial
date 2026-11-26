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


if __name__ == '__main__':
    unittest.main()
