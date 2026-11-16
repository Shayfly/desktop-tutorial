"""The shared reference store (migration 043, omni_prod/reference_store.py): the contract, and the migration file.

The PostgreSQL twin of the contract tests is tests/test_reference_store_pg.py (intake-budget-pg, real database).
"""
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from omni_prod import reference_store as RS
from omni_prod.migrations import discover_migrations
from tests.reference_cards_fixture import card

ROOT = Path(__file__).resolve().parent.parent
UP = ROOT / 'infra' / 'postgres' / '043_reference_store.sql'
DOWN = ROOT / 'infra' / 'postgres' / 'rollback' / '043_reference_store.down.sql'
TABLES = ['reference_cards', 'reference_card_components', 'category_adjacency', 'reference_offers',
          'offer_rejections', 'offer_alerts', 'collect_queue']
NOW = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)


def _statements(sql):
    body = '\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--'))
    return [re.sub(r'\s+', ' ', s).strip() for s in body.split(';') if s.strip()]


class Migration043(unittest.TestCase):
    def test_043_is_the_newest_and_the_manifest_requires_it(self):
        # 2026-11-15 (P0-c, migration 044): this pinned 043 as the newest migration, which every later migration must
        # move. What it means is kept: 043 is shipped, and the code requires at least it.
        from omni_prod.schema_manifest import EXPECTED_VERSIONS, REQUIRED_MIGRATION
        found = {m.version: m.name for m in discover_migrations(UP.parent)}
        self.assertEqual(found.get(43), 'reference_store')
        self.assertIn(43, EXPECTED_VERSIONS)
        self.assertGreaterEqual(REQUIRED_MIGRATION, 43)
        self.assertEqual(REQUIRED_MIGRATION, max(found))        # the newest shipped migration is the required one

    def test_additive_only_and_touches_nothing_that_exists(self):
        stmts = _statements(UP.read_text())
        self.assertTrue(all(s.startswith('CREATE ') and 'IF NOT EXISTS' in s for s in stmts))
        self.assertNotRegex(UP.read_text(), r'(?i)\b(drop|alter|truncate|delete|update)\b')
        created = [re.search(r'CREATE TABLE IF NOT EXISTS (\w+)', s).group(1) for s in stmts if s.startswith('CREATE TABLE')]
        self.assertEqual(created, TABLES)
        self.assertTrue(set(re.findall(r'REFERENCES (\w+)', UP.read_text())) <= set(TABLES))

    def test_the_rollback_removes_exactly_what_043_creates(self):
        self.assertNotIn(DOWN.name, {m.path.name for m in discover_migrations(UP.parent)})
        stmts = _statements(DOWN.read_text())
        dropped = [re.search(r'DROP TABLE IF EXISTS (\w+)', s).group(1) for s in stmts if 'DROP TABLE' in s]
        indexes_up = re.findall(r'CREATE INDEX IF NOT EXISTS (\w+)', UP.read_text())
        indexes_down = re.findall(r'DROP INDEX IF EXISTS (\w+)', DOWN.read_text())
        self.assertEqual(dropped, list(reversed(TABLES)))
        self.assertEqual(sorted(indexes_down), sorted(indexes_up))
        self.assertEqual((stmts[0], stmts[-1]), ('BEGIN', 'COMMIT'))
        self.assertIn('DELETE FROM schema_migrations WHERE version = 43', stmts)
        self.assertNotRegex(DOWN.read_text(), r'(?i)\bcascade\b')

    def test_the_hard_rules_are_repeated_in_the_database(self):
        sql = ' '.join(UP.read_text().split())
        self.assertIn("CHECK (decision <> 'approved' OR decided_by IN ('michael', 'shai'))", sql)
        self.assertIn("retired_by TEXT NULL CHECK (retired_by IN ('shai'))", sql)
        self.assertIn('cross_vertical BOOLEAN NOT NULL DEFAULT false', sql)
        self.assertIn("adjacency_rank SMALLINT NOT NULL DEFAULT 0 CHECK (adjacency_rank BETWEEN 0 AND 2)", sql)


class Contract(unittest.TestCase):
    def store(self):
        return RS.MemoryReferenceStore()

    def test_a_card_outside_the_369_schema_is_never_stored(self):
        s = self.store()
        bad = card(1)
        bad['skeleton']['notes'] = 'בשר טרי ב-49.90'           # the free text #369 removed
        with self.assertRaises(RS.ReferenceStoreError):
            s.add_card(bad, extraction_version='x1')
        scout = card(2, decided_by='scout')                   # an approval without a human
        with self.assertRaises(RS.ReferenceStoreError):
            s.add_card(scout, extraction_version='x1')
        self.assertEqual(s.approved_for('butcher', now=NOW), [])

    def test_stale_is_ranked_lower_and_marked_never_removed(self):
        s = self.store()
        old = (NOW - timedelta(days=91)).strftime('%Y-%m-%dT%H:%M:%SZ')
        s.add_card(card(1, total=10, captured_at=old), extraction_version='x1')
        s.add_card(card(2, total=8), extraction_version='x1')
        rows = s.approved_for('butcher', now=NOW)
        self.assertEqual([r.card_id for r in rows], [card(2)['card_id'], card(1)['card_id']])
        self.assertEqual([r.effective_status(NOW) for r in rows], ['fresh', 'stale'])

    def test_weak_last_neighbours_after_the_category_rejected_never(self):
        s = self.store()
        s.add_card(card(1, total=10), extraction_version='x1', status='weak')
        s.add_card(card(2, total=8), extraction_version='x1', adjacency_rank=1)
        s.add_card(card(3, total=8), extraction_version='x1')
        s.add_card(card(4, status='rejected', decided_by='scout', reason_code='carousel'), extraction_version='x1')
        self.assertEqual([r.card_id for r in s.approved_for('butcher', now=NOW)],
                         [card(3)['card_id'], card(2)['card_id'], card(1)['card_id']])

    def test_only_the_owner_retires_a_card(self):
        s = self.store()
        s.add_card(card(1), extraction_version='x1')
        with self.assertRaises(RS.ReferenceStoreError):
            s.retire(card(1)['card_id'], by='michael')
        self.assertEqual(len(s.approved_for('butcher', now=NOW)), 1)
        s.retire(card(1)['card_id'], by='shai')
        self.assertEqual(s.approved_for('butcher', now=NOW), [])

    def test_neighbours_in_rank_order_with_cross_vertical_marked(self):
        s = self.store()
        s.set_adjacent('vets', [('clinics', False), ('pet_shops', True)])          # appendix B
        self.assertEqual(s.adjacent('vets'), [{'category': 'clinics', 'cross_vertical': False, 'rank': 1},
                                              {'category': 'pet_shops', 'cross_vertical': True, 'rank': 2}])
        for bad in ([('vets', False)], [('clinics', False), ('clinics', True)]):
            with self.assertRaises(RS.ReferenceStoreError):
                s.set_adjacent('vets', bad)
        self.assertEqual(s.adjacent('fish'), [])                                 # no row: no fallback to clothes

    def test_a_card_is_never_more_than_two_links_away(self):
        with self.assertRaises(RS.ReferenceStoreError):
            self.store().add_card(card(1), extraction_version='x1', adjacency_rank=3)

    def test_a_collect_request_is_kept_once_and_shown(self):
        s = self.store()
        s.request_collect('butcher', 'domain_rejected', 'brf_1')
        s.request_collect('butcher', 'domain_rejected', 'brf_2')
        self.assertEqual(s.open_collect_requests(), [{'category': 'butcher', 'reason': 'domain_rejected',
                                                      'brief_id': 'brf_1'}])
        with self.assertRaises(RS.ReferenceStoreError):
            s.request_collect('butcher', 'because')


if __name__ == '__main__':
    unittest.main()
