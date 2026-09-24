"""M4.9 directive item 11 -- "COMPLETE VERSION LIFECYCLE": after obtaining
the genuine READY_FOR_REVIEW candidate (tests/test_m49_clean_room.py,
task #49 -- NOT mocked repository state; see that file's own docstring for
why this milestone is the first to reach READY_FOR_REVIEW without a manual
`PostgresModificationRepository.complete(status='READY_FOR_REVIEW', ...)`
shortcut), this file:
  A. accepts it (real HTTP POST .../accept against real Postgres)
  B. verifies the real Postgres current version really moved to that
     candidate's content
  C. verifies the corresponding ProductSpec/current() state matches
  D. performs a real rollback (real HTTP POST .../rollback) back to the
     original seed version
  E. verifies the previous accepted (seed) version is restored EXACTLY --
     byte-identical repository content, real diff-free comparison

"No mocked repository state for this final lifecycle proof": this file
reuses the exact real modification/project/version the real clean-room
worker pipeline produced in tests/test_m49_clean_room.py (IDs read from
/tmp/m49_clean_room_ids.json, written by that test) rather than manually
constructing a READY_FOR_REVIEW row. Run tests/test_m49_clean_room.py
first in the same database.

Must run standalone (own process), same reason as every other live-infra
file in this repo:
  PYTHONPATH=/tmp/m4d2b_vendor:/tmp/m49_pytest_vendor \\
  python3.11 -m pytest -q tests/test_m49_lifecycle.py
"""
from __future__ import annotations

import json
import os
import sys
import unittest


def _skip_reason() -> str | None:
    try:
        import psycopg  # noqa: F401
        import fastapi  # noqa: F401
    except ImportError as exc:
        return f'live-infra dependency not importable ({exc})'
    if not os.path.exists('/tmp/m49_clean_room_ids.json'):
        return ('/tmp/m49_clean_room_ids.json not found -- run tests/test_m49_clean_room.py '
                'first in the same database to produce a real READY_FOR_REVIEW candidate')
    with open('/tmp/m49_clean_room_ids.json') as f:
        ids = json.load(f)
    try:
        conn = psycopg.connect(ids['database_url'], connect_timeout=3)
        conn.close()
    except Exception as exc:  # pragma: no cover - environment probe
        return f'cannot reach {ids["database_url"]!r}: {exc}'
    if 'omni_prod.investor_app' in sys.modules:
        return ('omni_prod.investor_app was already imported by another test module in this '
                'process -- run this file standalone: python3 -m pytest -q tests/test_m49_lifecycle.py')
    return None


_SKIP = _skip_reason()

if _SKIP is None:
    with open('/tmp/m49_clean_room_ids.json') as f:
        _IDS = json.load(f)

    os.environ['OMNI_CREATOR_PERSISTENCE'] = 'postgres'
    os.environ['OMNI_DATABASE_URL'] = _IDS['database_url']
    os.environ['OMNI_REDIS_URL'] = os.environ.get('M49_REDIS_URL', 'redis://127.0.0.1:6379/0')
    os.environ['OMNI_BILLING_ADMIN_KEY'] = _IDS['billing_admin_key']
    # Must match the exact secret tests/test_m49_clean_room.py used to sign
    # the stashed auth token -- OMNI_SECRET_KEY is what
    # investor_app.py's JWT auth verifies against, and a mismatch here
    # produces a real (but here, unwanted) 403 'invalid authentication'.
    os.environ.setdefault('OMNI_SECRET_KEY', 'm49-clean-room-live-worker-secret-' + 'x' * 32)
    os.environ['OMNI_ENABLE_LIVE_BUILD'] = '1'

    from fastapi.testclient import TestClient
    import omni_prod.investor_app as iapp
    from omni_prod.workspace import PostgresProjectWorkspace
    from tests.test_m4d2_live_postgres import DiskArtifactStore

    assert iapp._v28_pool is not None
    iapp._v28.engine.workspace = PostgresProjectWorkspace(iapp._v28_pool, DiskArtifactStore(_IDS['artifact_root']))


@unittest.skipIf(_SKIP, _SKIP)
class CompleteVersionLifecycleTests(unittest.TestCase):
    """Item 11's A-E, against the real clean-room modification, no mocks."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(iapp.app)
        cls.h = {'Authorization': 'Bearer ' + _IDS['token']}
        cls.project_id = _IDS['project_id']
        cls.project_key = _IDS['project_key']
        cls.modification_id = _IDS['modification_id']
        cls.seed_version_id = _IDS['version_id']

    def test_A_through_E_accept_verify_rollback_verify(self):
        from omni_prod.modification_repository import PostgresModificationRepository
        mods_repo = PostgresModificationRepository(iapp._v28_pool)

        # Precondition, re-verified directly (not assumed from task #49's
        # earlier run): the modification is still genuinely READY_FOR_REVIEW
        # and the project's current version is still the untouched seed.
        details_before = mods_repo.get_details(self.modification_id, self.project_key)
        self.assertEqual(details_before.status, 'READY_FOR_REVIEW', details_before)
        seed_version = iapp._v28.engine.workspace.current(self.project_key)
        self.assertEqual(seed_version.id, self.seed_version_id)
        seed_repository = dict(seed_version.repository())
        self.assertIn('index.html', seed_repository)

        db_candidate = mods_repo.get_candidate(self.modification_id, self.project_key)
        candidate_repository = dict(db_candidate['repository'])
        candidate_spec_title = db_candidate['spec'].title

        # ---- A. Accept it (real HTTP call). ----
        accept = self.client.post(
            f'/api/v28/projects/{self.project_id}/modifications/{self.modification_id}/accept',
            headers=self.h, json={})
        self.assertEqual(accept.status_code, 200, accept.text)
        outcome = accept.json()
        self.assertTrue(outcome['accepted'], outcome)
        new_version_id = outcome['new_version_id']
        self.assertNotEqual(new_version_id, self.seed_version_id)

        # ---- B. Verify Postgres current version really moved. ----
        current_after_accept = iapp._v28.engine.workspace.current(self.project_key)
        self.assertEqual(current_after_accept.id, new_version_id,
                          'PostgreSQL current() must now point at the accepted candidate version')
        self.assertEqual(dict(current_after_accept.repository()), candidate_repository,
                          "the newly-current version's stored repository must be byte-identical to "
                          "the accepted candidate (nothing regenerated/mocked on accept)")
        # Direct raw-row check too, not only through the workspace wrapper.
        import psycopg
        conn = psycopg.connect(_IDS['database_url'])
        cur = conn.cursor()
        cur.execute("SELECT parent_id FROM project_versions WHERE id = %s AND project_id = %s",
                    (new_version_id, self.project_key))
        row = cur.fetchone()
        self.assertIsNotNone(row, 'the accepted version must be a real row in project_versions')
        self.assertEqual(row[0], self.seed_version_id, "the new version's parent must be the seed version")

        details_after_accept = mods_repo.get_details(self.modification_id, self.project_key)
        self.assertEqual(details_after_accept.status, 'ACCEPTED', details_after_accept)
        self.assertEqual(details_after_accept.promoted_version_id, new_version_id)
        self.assertIsNotNone(details_after_accept.accepted_at)

        # ---- C. Verify corresponding ProductSpec/current state. ----
        cur.execute("SELECT spec_json FROM project_version_specs WHERE version_id = %s AND project_id = %s",
                    (new_version_id, self.project_key))
        spec_row = cur.fetchone()
        self.assertIsNotNone(spec_row, 'the accepted version must have a real, persisted ProductSpec row')
        persisted_spec = spec_row[0] if isinstance(spec_row[0], dict) else json.loads(spec_row[0])
        self.assertEqual(persisted_spec['title'], candidate_spec_title)

        status_route = self.client.get(
            f'/api/v28/projects/{self.project_id}/modifications/{self.modification_id}', headers=self.h)
        self.assertEqual(status_route.json()['status'], 'ACCEPTED')
        self.assertEqual(status_route.json()['promoted_version_id'], new_version_id)

        # ---- D. Perform rollback (real HTTP call), back to the seed. ----
        rollback = self.client.post(
            f'/api/v28/projects/{self.project_id}/rollback', headers=self.h,
            json={'target_version_id': self.seed_version_id, 'message': 'm49 lifecycle rollback proof'})
        self.assertEqual(rollback.status_code, 200, rollback.text)
        rollback_outcome = rollback.json()
        rollback_version_id = rollback_outcome.get('new_version_id') or rollback_outcome.get('version_id')
        self.assertIsNotNone(rollback_version_id, rollback_outcome)
        self.assertNotEqual(rollback_version_id, new_version_id)
        self.assertNotEqual(rollback_version_id, self.seed_version_id,
                             'rollback re-commits the seed content as a brand-new version -- '
                             'append-only, never rewrites/reuses the old row')

        # ---- E. Verify the previous accepted (seed) version is restored
        # EXACTLY -- byte-identical content, real comparison. ----
        current_after_rollback = iapp._v28.engine.workspace.current(self.project_key)
        self.assertEqual(current_after_rollback.id, rollback_version_id,
                          'PostgreSQL current() must now point at the new rollback version')
        restored_repository = dict(current_after_rollback.repository())
        self.assertEqual(restored_repository, seed_repository,
                          "the rollback version's repository must be BYTE-IDENTICAL to the original "
                          "seed repository -- no regeneration, no drift")
        self.assertNotEqual(restored_repository, candidate_repository,
                             'sanity: the restored content must differ from the (superseded) accepted candidate')

        cur.execute("SELECT parent_id FROM project_versions WHERE id = %s AND project_id = %s",
                    (rollback_version_id, self.project_key))
        rollback_row = cur.fetchone()
        self.assertIsNotNone(rollback_row)
        self.assertEqual(rollback_row[0], new_version_id,
                          "the rollback version's parent is the version it was rolled back FROM "
                          "(the accepted candidate), matching this history's real append-only chain")

        cur.execute("SELECT count(*) FROM project_versions WHERE project_id = %s", (self.project_key,))
        total_versions = cur.fetchone()[0]
        self.assertEqual(total_versions, 3,
                          f'expected exactly 3 real versions in the full history (seed -> accepted -> '
                          f'rollback), got {total_versions}')

        cur.close()
        conn.close()


if __name__ == '__main__':
    unittest.main()
