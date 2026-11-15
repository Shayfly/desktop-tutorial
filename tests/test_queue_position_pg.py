"""Michael 2026-11-15 ("מקביליות -- חיווי תור"), on real PostgreSQL: a queued build tells its customer how many jobs are
ahead of it on the single worker (builds and modifications share omni-builds, first in first out).

The reproduction is the only overlap of the last 30 days: bld_d87842fb was created at 05:53:18 on 2026-11-09 while
bld_5b2e8f58 ran (05:52:34-06:00:41) and waited 461 s with no word on screen. Times as stored in build_jobs.
Runs in intake-budget-pg (skipped elsewhere without M4D2_DATABASE_URL)."""
from __future__ import annotations

import os
import pathlib
import unittest
import uuid

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
RUNNING = ('bld_5b2e8f58bee941ed82af9525c6324c11', '2026-11-09T05:52:27.083Z')
WAITING = ('bld_d87842fb27cf47968207f6149a562088', '2026-11-09T05:53:18.451Z')


class QueuePosition(unittest.TestCase):
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
        cls.dbname = f'qp_{uuid.uuid4().hex[:10]}'
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

    def setUp(self):
        from omni_prod.job_repository import PostgresBuildRepository
        self.jobs = PostgresBuildRepository(self.pool)
        with self.pool.connection() as conn:
            conn.execute('DELETE FROM modification_requests')
            conn.execute('DELETE FROM build_jobs')
            conn.commit()

    def build(self, build_id, created, status, project='prj_a'):
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO build_jobs(id, project_id, version_id, status, created_at) VALUES (%s,%s,%s,%s,%s)',
                         (build_id, project, f'v_{build_id[-6:]}', status, created))
            conn.commit()

    def modification(self, created, status):
        vid = f'v_{uuid.uuid4().hex[:8]}'
        with self.pool.connection() as conn:
            conn.execute("INSERT INTO project_versions(id, project_id, repository_sha256, message) VALUES (%s,'prj_b',%s,'m')",
                         (vid, '0' * 64))
            conn.execute('INSERT INTO modification_requests(id, project_id, user_id, source_version_id, '
                         'source_spec_version_id, followup, status, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                         (f'mod_{uuid.uuid4().hex[:8]}', 'prj_b', 'usr_b', vid, vid, 'x', status, created))
            conn.commit()

    def test_the_build_of_2026_11_09_had_one_job_ahead(self):
        self.build(RUNNING[0], RUNNING[1], 'RUNNING', project='prj_other')
        self.build(WAITING[0], WAITING[1], 'QUEUED')
        self.assertEqual(self.jobs.queue_ahead(WAITING[0], internal_project_id='prj_a'), 1)
        from tests.evidence_notice import notice
        notice('queue position', f'{WAITING[0][:12]} created while {RUNNING[0][:12]} ran: 1 job ahead')

    def test_next_in_line_is_zero_and_a_later_job_does_not_count(self):
        self.build(WAITING[0], WAITING[1], 'QUEUED')
        self.build('bld_later', '2026-11-09T05:59:00Z', 'QUEUED', project='prj_other')
        self.assertEqual(self.jobs.queue_ahead(WAITING[0], internal_project_id='prj_a'), 0)

    def test_modifications_ahead_count_and_finished_jobs_do_not(self):
        self.build(WAITING[0], WAITING[1], 'QUEUED')
        self.modification('2026-11-09T05:50:00Z', 'RUNNING')
        self.modification('2026-11-09T05:51:00Z', 'QUEUED')
        self.modification('2026-11-09T05:51:30Z', 'READY_FOR_REVIEW')          # waits for the customer, not the worker
        self.build('bld_done', '2026-11-09T05:40:00Z', 'READY', project='prj_other')
        self.build('bld_failed', '2026-11-09T05:41:00Z', 'FAILED', project='prj_other')
        self.assertEqual(self.jobs.queue_ahead(WAITING[0], internal_project_id='prj_a'), 2)

    def test_a_running_build_has_no_position(self):
        self.build(RUNNING[0], RUNNING[1], 'RUNNING')
        self.assertIsNone(self.jobs.queue_ahead(RUNNING[0], internal_project_id='prj_a'))

    def test_another_projects_build_is_not_readable(self):
        self.build(WAITING[0], WAITING[1], 'QUEUED')
        with self.assertRaises(KeyError):
            self.jobs.queue_ahead(WAITING[0], internal_project_id='prj_intruder')


if __name__ == '__main__':
    unittest.main()
