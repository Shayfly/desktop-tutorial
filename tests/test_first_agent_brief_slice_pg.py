"""Slice 3 on real PostgreSQL with the real BriefRepository: the butcher's production brief (rev 8) is saved, the
first agent writes its structure card and a reference, then reverts. Three immutable revisions; the third has the
first one's exact content and fingerprint; the approval fingerprint of revision 2 carries the structure.
Runs in intake-budget-pg (skipped elsewhere without M4D2_DATABASE_URL)."""
from __future__ import annotations

import json
import os
import pathlib
import unittest
import uuid

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
FIX = pathlib.Path(__file__).resolve().parent / 'fixtures' / 'butcher_prj_fV8kB7FwuNimGw.json'


class BriefSliceOnPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        root = pathlib.Path(__file__).resolve().parents[1]
        cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        cls.dbname = f'bs_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(root / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def test_write_and_revert_are_revisions_and_the_revert_is_byte_for_byte(self):
        from omni_prod.brief_repository import PostgresBriefRepository
        from omni_prod.discovery import Brief
        from omni_prod.fact_canon import build_canon
        from omni_prod.first_agent import brief_slice as BS
        from omni_prod.first_agent.structure import build_card
        fx = json.loads(FIX.read_text())
        user, project = f'usr_{uuid.uuid4().hex[:8]}', f'prj_{uuid.uuid4().hex[:8]}'
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO creator_accounts (id, email, password_hash, salt_b64) VALUES (%s,%s,%s,%s)',
                         (user, f'{user}@example.com', 'x', 'x'))
            conn.execute("INSERT INTO creator_projects (id, owner_id, title) VALUES (%s, %s, 't')", (project, user))
            conn.commit()
        repo = PostgresBriefRepository(self.pool)
        brief = Brief.from_dict(fx['brief'])
        first = repo.save(project_id=project, account_id=user, brief=brief, expected_revision=0)
        self.assertEqual(first.fingerprint, fx['fingerprint'])                      # stored as in production
        card = build_card(brief.prompt, canon=build_canon(brief.prompt), vertical='butcher')
        w = BS.write(repo, project_id=project, account_id=user, structure=[card], references='קישור')
        self.assertEqual(w['row'].revision, 2)
        self.assertNotEqual(w['row'].fingerprint, first.fingerprint)               # the approval binds the structure
        back = BS.revert(repo, project_id=project, account_id=user, undo=w['undo'])
        self.assertEqual(back['row'].revision, 3)
        self.assertEqual(back['row'].fingerprint, first.fingerprint)
        with self.pool.connection() as conn:
            rows = conn.execute('SELECT revision, fingerprint, brief_json ? %s FROM project_briefs WHERE project_id=%s '
                                'ORDER BY revision', ('structure', project)).fetchall()
        self.assertEqual([(r[0], r[2]) for r in rows], [(1, False), (2, True), (3, False)])   # nothing deleted
        from tests.evidence_notice import notice
        notice('brief slice', f'rev1 {first.fingerprint[:12]} -> rev2 {w["row"].fingerprint[:12]} (structure) '
                              f'-> rev3 {back["row"].fingerprint[:12]} (reverted, equal to rev1)')


if __name__ == '__main__':
    unittest.main()
