"""first_pass_yield, read every day from production (the founder's metric; 2026-11-21: a month unread).

Pure counting runs everywhere. RealPostgres writes build_jobs rows with real JSONB evidence into a fresh database built
from the platform's migrations and reads them back through the tool's own read path; it runs in intake-budget-pg
(M4D2_DATABASE_URL; no skip there). Mutations: tests/negative_controls/first_pass_yield.json.
"""
import datetime as dt
import json
import os
import pathlib
import sys
import tempfile
import unittest
import uuid

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import first_pass_yield as FPY  # noqa: E402

NOW = dt.datetime(2026, 11, 21, 4, 23, tzinfo=dt.timezone.utc)


def row(i, status='failed', days_ago=1.0, recorded=True, first_pass=False, taxonomy=None, error_code=None):
    return {'id': f'bld_{i}', 'status': status, 'created_at': NOW - dt.timedelta(days=days_ago),
            'error_code': error_code, 'recorded': recorded, 'first_pass': first_pass, 'taxonomy': taxonomy or []}


def blocker(layer, failure_type, round_index=0):
    return {'layer': layer, 'failure_type': failure_type, 'round_index': round_index, 'was_repaired': True}


class Counting(unittest.TestCase):
    def test_the_yield_is_first_pass_over_finished_builds_and_cancelled_ones_are_apart(self):
        rows = [row(1, 'ready', first_pass=True), row(2, 'ready'), row(3, 'failed'), row(4, 'cancelled')]
        w = FPY.summarize(rows, NOW)['windows']['7']
        self.assertEqual((w['first_pass'], w['finished'], w['cancelled'], w['ready']), (1, 3, 1, 2))
        self.assertEqual(w['first_pass_yield'], round(1 / 3, 4))

    def test_a_failed_build_is_never_a_first_pass_whatever_its_flag_says(self):
        w = FPY.summarize([row(1, 'failed', first_pass=True), row(2, 'ready', first_pass=True)], NOW)['windows']['7']
        self.assertEqual(w['first_pass'], 1)

    def test_a_finished_build_without_a_worker_record_counts_as_not_first_pass_and_is_named(self):
        rows = [row(1, 'ready', first_pass=True),
                row(2, 'failed', recorded=False, first_pass=True, error_code='worker_lost')]
        w = FPY.summarize(rows, NOW)['windows']['7']
        self.assertEqual((w['first_pass'], w['finished'], w['recorded']), (1, 2, 1))
        self.assertEqual(w['unrecorded_by_error_code'], {'worker_lost': 1})

    def test_the_windows_are_by_creation_time(self):
        rows = [row(1, 'ready', days_ago=0.5), row(2, 'failed', days_ago=3), row(3, 'failed', days_ago=20),
                row(4, 'failed', days_ago=40)]
        ws = FPY.summarize(rows, NOW)['windows']
        self.assertEqual([ws[d]['finished'] for d in ('1', '7', '30')], [1, 2, 3])

    def test_no_finished_build_is_no_yield_not_zero(self):
        w = FPY.summarize([row(1, 'cancelled')], NOW)['windows']['7']
        self.assertIsNone(w['first_pass_yield'])

    def test_what_stopped_the_first_pass_counts_round_zero_once_per_build(self):
        noisy = [blocker('sandbox', 'remote_verification_failed')] * 5 + [blocker('review', 'qa_review_(spec)', 1)]
        rows = [row(1, 'failed', taxonomy=noisy), row(2, 'ready', taxonomy=[blocker('sandbox', 'remote_verification_failed')])]
        top = dict(FPY.summarize(rows, NOW)['windows']['7']['top_failure_categories'])
        self.assertEqual(top, {'sandbox:remote_verification_failed': 2})


    def test_a_preflight_plan_repair_is_not_what_stopped_the_first_pass(self):
        # 2026-11-21: preflight_plan_coverage topped the list (18 builds) although it costs no round and every one
        # of those builds also failed round 0 on a real chain failure
        rows = [row(1, 'failed', taxonomy=[blocker('preflight', 'preflight_plan_coverage'),
                                           blocker('sandbox', 'remote_verification_failed')])]
        top = dict(FPY.summarize(rows, NOW)['windows']['7']['top_failure_categories'])
        self.assertEqual(top, {'sandbox:remote_verification_failed': 1})


class Verdict(unittest.TestCase):
    def test_finished_builds_with_no_record_at_all_is_a_broken_wiring(self):
        s = FPY.summarize([row(1, 'failed', recorded=False), row(2, 'ready', recorded=False)], NOW)
        self.assertEqual(FPY.verdict(s)[0], 1)

    def test_a_zero_yield_is_a_finding_not_an_error(self):
        s = FPY.summarize([row(1, 'failed'), row(2, 'ready')], NOW)
        self.assertEqual(FPY.verdict(s), (0, 'reported'))

    def test_a_quiet_week_is_not_an_error(self):
        self.assertEqual(FPY.verdict(FPY.summarize([], NOW))[0], 0)


class FakeCursor:
    def __init__(self, rows):
        self.description = [(n,) for n in ('id', 'status', 'created_at', 'error_code', 'recorded', 'first_pass',
                                           'taxonomy')]
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakeConn:
    def __init__(self, rows):
        self.sql, self.rows, self.rolled_back = [], rows, False

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.sql.append(sql.strip())
        return FakeCursor(self.rows)

    def rollback(self):
        self.rolled_back = True


class ReadPath(unittest.TestCase):
    def test_the_read_is_a_read_only_transaction_and_ends_in_a_rollback(self):
        conn = FakeConn([('bld_1', 'ready', NOW, None, True, True, '[]')])
        rows = FPY.read_rows('postgresql://x', NOW, connect=lambda url, connect_timeout: conn)
        self.assertEqual(conn.sql[0], 'SET TRANSACTION READ ONLY')
        self.assertTrue(conn.rolled_back)
        self.assertEqual(rows[0]['taxonomy'], [])

    def test_the_query_only_reads(self):
        words = set(FPY.QUERY.upper().replace('(', ' ').replace(')', ' ').split())
        self.assertFalse(words & {'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE', 'CREATE', 'GRANT'})
        self.assertIn('FROM BUILD_JOBS', ' '.join(FPY.QUERY.upper().split()))


class Cli(unittest.TestCase):
    def run_main(self, url, connect):
        out = pathlib.Path(tempfile.mkdtemp()) / 'fpy.json'
        summary = out.with_name('summary.md')
        old = os.environ.get('OMNI_DATABASE_URL')
        os.environ['OMNI_DATABASE_URL'] = url
        try:
            rc = FPY.main(['--out', str(out), '--summary', str(summary)], connect=connect, now=NOW)
        finally:
            if old is None:
                os.environ.pop('OMNI_DATABASE_URL', None)
            else:
                os.environ['OMNI_DATABASE_URL'] = old
        return rc, out, summary

    def test_no_url_is_exit_2_and_no_file(self):
        rc, out, _ = self.run_main('', None)
        self.assertEqual(rc, 2)
        self.assertFalse(out.exists())

    def test_an_unreachable_database_is_exit_2_and_no_file(self):
        def refuse(url, connect_timeout):
            raise ConnectionError('refused')
        rc, out, _ = self.run_main('postgresql://x', refuse)
        self.assertEqual(rc, 2)
        self.assertFalse(out.exists())

    def test_a_report_writes_the_numbers_and_the_summary(self):
        conn = FakeConn([('bld_1', 'ready', NOW - dt.timedelta(hours=2), None, True, False,
                          json.dumps([blocker('sandbox', 'remote_verification_failed')]))])
        rc, out, summary = self.run_main('postgresql://x', lambda url, connect_timeout: conn)
        self.assertEqual(rc, 0)
        data = json.loads(out.read_text())
        self.assertEqual(data['windows']['7']['finished'], 1)
        self.assertIn('| 7d | 0/1 | 0% |', summary.read_text())


class TheDailyJob(unittest.TestCase):
    def setUp(self):
        self.doc = yaml.safe_load((ROOT / '.github/workflows/first-pass-yield.yml').read_text(encoding='utf-8'))

    def test_it_runs_every_day_and_by_hand(self):
        on = self.doc.get('on') or self.doc.get(True)
        cron = on['schedule'][0]['cron'].split()
        self.assertEqual(cron[2:], ['*', '*', '*'])
        self.assertIn('workflow_dispatch', on)

    def test_it_can_only_read_the_repository_and_never_pushes(self):
        self.assertEqual(self.doc['permissions'], {'contents': 'read'})
        text = (ROOT / '.github/workflows/first-pass-yield.yml').read_text(encoding='utf-8')
        for word in ('git push', 'git commit', 'gh pr', 'contents: write'):
            self.assertNotIn(word, text)

    def test_it_reads_production_through_the_tool(self):
        steps = self.doc['jobs']['report']['steps']
        read = next(s for s in steps if str(s.get('name', '')).startswith('Read first_pass_yield'))
        self.assertEqual(read['env']['OMNI_DATABASE_URL'], '${{ secrets.OMNI_DATABASE_URL }}')
        self.assertIn('tools/first_pass_yield.py', read['run'])


class RealPostgres(unittest.TestCase):
    """build_jobs rows with real JSONB evidence, read back through the tool's own path."""

    @classmethod
    def setUpClass(cls):
        url = os.getenv('M4D2_DATABASE_URL', '').strip()
        if not url:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        import psycopg
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        cls.admin = psycopg.connect(url, autocommit=True, connect_timeout=5)
        cls.dbname = f'fpy_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = url.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
            for i, (status, ev) in enumerate([
                    ('ready', {'first_pass': True, 'failure_taxonomy': []}),
                    ('ready', {'first_pass': False, 'failure_taxonomy': [blocker('review', 'qa_review_(spec)')]}),
                    ('failed', {'first_pass': False, 'failure_taxonomy': 'not-a-list'}),
                    ('failed', {'billing': 'released', 'reaped_by': 'reaper'}),             # worker lost: no record
                    ('failed', {'first_pass': 'maybe'}),                                     # not a boolean
                    ('cancelled', {})]):
                conn.execute('INSERT INTO build_jobs (id, project_id, status, created_at, evidence_json, error_code) '
                             'VALUES (%s, %s, %s, %s, %s::jsonb, %s)',
                             (f'bld_fpy{i}', 'prj_fpy', status, NOW - dt.timedelta(hours=i + 1), json.dumps(ev),
                              'worker_lost' if 'reaped_by' in ev else None))

    @classmethod
    def tearDownClass(cls):
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def test_the_real_rows_are_counted_as_the_worker_meant_them(self):
        rows = FPY.read_rows(self.url, NOW - dt.timedelta(days=30))
        self.assertEqual(len(rows), 6)
        w = FPY.summarize(rows, NOW)['windows']['1']
        self.assertEqual((w['finished'], w['ready'], w['first_pass'], w['cancelled']), (5, 2, 1, 1))
        self.assertEqual(w['recorded'], 4)                      # the reaped build carries no first_pass key
        self.assertEqual(w['unrecorded_by_error_code'], {'worker_lost': 1})
        self.assertEqual(dict(w['top_failure_categories']), {'review:qa_review_(spec)': 1})

    def test_the_read_cannot_write(self):
        import psycopg
        with psycopg.connect(self.url) as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            with self.assertRaises(psycopg.errors.ReadOnlySqlTransaction):
                conn.execute("UPDATE build_jobs SET status = 'ready' WHERE id = 'bld_fpy5'")


if __name__ == '__main__':
    unittest.main()
