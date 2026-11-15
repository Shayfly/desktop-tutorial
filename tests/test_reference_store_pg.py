"""PostgresReferenceStore on a real database (migration 043 applied by the intake-budget-pg job before the tests).

Same contract as tests/test_reference_store.py, plus what only the database can prove: its CHECK constraints refuse
what the code refuses (an approval without a human, a retirement by anyone but the owner, a third neighbour), and a
card changed in place is never served (sha256).
"""
import os
import unittest
from datetime import datetime, timedelta, timezone

from tests.reference_cards_fixture import card

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
NOW = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)


class PostgresReferenceStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        import pathlib
        import uuid
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        root = pathlib.Path(__file__).resolve().parents[1]
        cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        cls.dbname = f'rs_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:             # every migration, 043 on top of all of them
            run = apply_migrations(conn, discover_migrations(root / 'infra' / 'postgres'))
        assert 43 in run.applied_versions, run.applied_versions
        cls.pool = DatabasePool(cls.url)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def setUp(self):
        from omni_prod.reference_store import PostgresReferenceStore
        with self.pool.connection() as conn:
            for table in ('collect_queue', 'category_adjacency', 'reference_cards'):
                conn.execute(f'DELETE FROM {table}')
        self.store = PostgresReferenceStore(self.pool)

    def test_order_stale_and_retire_on_the_real_tables(self):
        from omni_prod.reference_store import ReferenceStoreError
        old = (NOW - timedelta(days=91)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.store.add_card(card(901, total=10, captured_at=old), extraction_version='x1')
        self.store.add_card(card(902, total=8), extraction_version='x1')
        self.store.add_card(card(903, total=10), extraction_version='x1', status='weak')
        rows = self.store.approved_for('butcher', now=NOW)
        self.assertEqual([r.card_id for r in rows], [card(902)['card_id'], card(901)['card_id'], card(903)['card_id']])
        self.assertEqual(rows[1].effective_status(NOW), 'stale')
        with self.assertRaises(ReferenceStoreError):
            self.store.retire(card(902)['card_id'], by='michael')
        self.store.retire(card(902)['card_id'], by='shai')
        self.assertNotIn(card(902)['card_id'], [r.card_id for r in self.store.approved_for('butcher', now=NOW)])

    def test_the_database_refuses_what_the_code_refuses(self):
        import json
        from psycopg import errors
        c = card(904, decided_by='scout')
        with self.assertRaises(errors.CheckViolation), self.pool.connection() as conn:
            conn.execute("INSERT INTO reference_cards (card_id, category, source_url, fetched_at, extraction_version, "
                         "status, decision, decided_by, card, card_sha256) VALUES (%s,'butcher',%s,now(),'x1','fresh',"
                         "'approved','scout',%s::jsonb,%s)", (c['card_id'], c['source']['url'], json.dumps(c), 'a' * 64))
        self.store.add_card(card(905), extraction_version='x1')
        with self.assertRaises(errors.CheckViolation), self.pool.connection() as conn:
            conn.execute("UPDATE reference_cards SET retired_at = now(), retired_by = 'michael' WHERE card_id = %s",
                         (card(905)['card_id'],))
        self.store.set_adjacent('pgt_vets', [('pgt_clinics', False), ('pgt_pets', True)])
        self.assertEqual([(a['category'], a['cross_vertical']) for a in self.store.adjacent('pgt_vets')],
                         [('pgt_clinics', False), ('pgt_pets', True)])
        with self.assertRaises(errors.CheckViolation), self.pool.connection() as conn:
            conn.execute("INSERT INTO category_adjacency (category, adjacent_category, rank) "
                         "VALUES ('pgt_fish', 'pgt_fish', 1)")
        with self.assertRaises(errors.CheckViolation), self.pool.connection() as conn:
            conn.execute("UPDATE reference_cards SET adjacency_rank = 3 WHERE card_id = %s", (card(905)['card_id'],))

    def test_a_card_changed_in_place_is_never_served(self):
        from omni_prod.reference_store import ReferenceStoreError
        self.store.add_card(card(906), extraction_version='x1')
        with self.pool.connection() as conn:
            conn.execute("UPDATE reference_cards SET card = jsonb_set(card, '{judge,total}', '10') WHERE card_id = %s",
                         (card(906)['card_id'],))
        with self.assertRaises(ReferenceStoreError):
            self.store.approved_for('butcher', now=NOW)

    def test_collect_requests_once_per_open_reason(self):
        self.store.request_collect('pgt_fish', 'domain_rejected', 'brf_1')
        self.store.request_collect('pgt_fish', 'domain_rejected', 'brf_2')
        mine = [r for r in self.store.open_collect_requests() if r['category'] == 'pgt_fish']
        self.assertEqual(mine, [{'category': 'pgt_fish', 'reason': 'domain_rejected', 'brief_id': 'brf_1'}])


if __name__ == '__main__':
    unittest.main()
