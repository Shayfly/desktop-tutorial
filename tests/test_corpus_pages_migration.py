"""Migration 045: the frozen reference corpus (the owner, 2026-11-17). A second collection run never duplicates a page
(UNIQUE url) and a captured page is never overwritten (a trigger). The PostgreSQL class needs M4D2_DATABASE_URL and
runs in intake-budget-pg: the migration and its rollback on a throw-away schema, against real constraints."""
from __future__ import annotations

import os
import unittest
import uuid
from pathlib import Path

from omni_prod.migrations import discover_migrations

ROOT = Path(__file__).resolve().parent.parent
UP = ROOT / 'infra' / 'postgres' / '045_corpus_pages.sql'
DOWN = ROOT / 'infra' / 'postgres' / 'rollback' / '045_corpus_pages.down.sql'
DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()


class TheFiles(unittest.TestCase):
    def test_045_is_discovered_and_its_rollback_drops_exactly_what_it_creates(self):
        self.assertIn(45, {m.version for m in discover_migrations(UP.parent)})
        up, down = UP.read_text(encoding='utf-8'), DOWN.read_text(encoding='utf-8')
        self.assertIn('CONSTRAINT corpus_pages_url_unique UNIQUE (url)', up)
        self.assertIn('CREATE TRIGGER corpus_pages_frozen', up)
        for obj in ('DROP TRIGGER IF EXISTS corpus_pages_frozen', 'DROP FUNCTION IF EXISTS corpus_pages_never_overwritten',
                    'DROP TABLE IF EXISTS corpus_pages'):
            self.assertIn(obj, down)


@unittest.skipUnless(DATABASE_URL, 'NOT_RUN: needs M4D2_DATABASE_URL (runs in intake-budget-pg)')
class OnPostgres(unittest.TestCase):
    def setUp(self):
        import psycopg
        self.conn = psycopg.connect(DATABASE_URL, autocommit=True)
        self.schema = 'corpus_' + uuid.uuid4().hex[:8]
        self.conn.execute(f'CREATE SCHEMA {self.schema}')
        self.conn.execute(f'SET search_path TO {self.schema}')
        self.conn.execute(UP.read_text(encoding='utf-8'))

    def tearDown(self):
        self.conn.execute(f'DROP SCHEMA {self.schema} CASCADE')
        self.conn.close()

    def insert(self, url, sha=None):
        self.conn.execute('INSERT INTO corpus_pages (url, category, city, fetched_at, html_sha256) '
                          "VALUES (%s, 'bakeries', 'חיפה', now(), %s)", (url, sha))

    def test_a_page_is_collected_once(self):
        import psycopg
        self.insert('https://example-bakery.co.il/')
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.insert('https://example-bakery.co.il/')

    def test_a_captured_page_is_never_overwritten(self):
        import psycopg
        self.insert('https://example-bakery.co.il/', sha='a' * 64)
        with self.assertRaises(psycopg.errors.RaiseException):
            self.conn.execute("UPDATE corpus_pages SET html_sha256 = %s", ('b' * 64,))
        self.conn.execute("UPDATE corpus_pages SET notes = 'checked'")          # a note may be added

    def test_the_rollback_removes_it(self):
        self.conn.execute(DOWN.read_text(encoding='utf-8'))
        exists = self.conn.execute("SELECT to_regclass(%s)", (f'{self.schema}.corpus_pages',)).fetchone()[0]
        self.assertIsNone(exists)


if __name__ == '__main__':
    unittest.main()
