"""The owner's definition of a good build (2026-11-22), counted from the database as it is -- no new definition."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import importlib.util
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('good_builds', ROOT / 'tools' / 'good_builds.py')
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

PASS = {'G1': {'mode': 'block', 'status': 'pass'}, 'HE': {'mode': 'warn', 'status': 'fail'}, 'G8': {'mode': 'warn'}}


def row(i, *, route='section_library', status='ready', rounds=1, gates=PASS, domain='hair-salon'):
    return {'id': f'bld_{i:032x}', 'status': status, 'created_at': '2026-11-23T10:00:00+00:00',
            'site_route': json.dumps({'route': route, 'domain': domain}), 'repair_rounds': rounds,
            'skill_gates': json.dumps(gates)}


DECISIONS = """- **2026-11-22, הבעלים — דגל הפריסה.**
  - **הבניות הטובות** (שורה לכל בנייה):
    - bld_00000000000000000000000000000001 — מספרה — הבעלים: ברמה.
    - bld_00000000000000000000000000000002 — עורך דין — הבעלים: ברמה.
  - המחיקה היא PR נפרד.
- **2026-11-21, הבעלים — התרגילים.** bld_00000000000000000000000000000009 is mentioned here, not under the heading.
"""


class TheThreeDatabaseConditions(unittest.TestCase):
    def test_a_ready_engine_build_with_two_rounds_and_no_blocking_failure_holds(self):
        j = G.judge(row(1, rounds=2))
        self.assertTrue(j['db_conditions_hold'])
        self.assertEqual(j['why_not'], [])

    def test_each_condition_fails_by_name(self):
        self.assertIn('not the new engine (site_route: legacy)', G.judge(row(1, route='legacy'))['why_not'])
        self.assertIn('status failed', G.judge(row(1, status='failed'))['why_not'])
        self.assertIn('3 repair rounds (at most 2)', G.judge(row(1, rounds=3))['why_not'])
        self.assertIn('no repair_rounds in the evidence', G.judge(row(1, rounds=None))['why_not'])
        bad = {**PASS, 'G5': {'mode': 'block', 'status': 'fail'}}
        self.assertIn('blocking gate failed: G5', G.judge(row(1, gates=bad))['why_not'])

    def test_a_warn_gate_failing_does_not_count_and_not_run_is_not_a_failure(self):
        self.assertEqual(G.blocking_failures(json.dumps(PASS)), [])


class TheOwnersWord(unittest.TestCase):
    def test_only_lines_under_the_heading_count(self):
        self.assertEqual(G.owner_said(DECISIONS), {'bld_00000000000000000000000000000001',
                                                   'bld_00000000000000000000000000000002'})

    def test_no_heading_no_approval(self):
        self.assertEqual(G.owner_said('nothing here bld_00000000000000000000000000000001'), set())


class TheCount(unittest.TestCase):
    def test_three_good_builds_in_three_domains_are_needed(self):
        rows = [row(1, domain='hair-salon'), row(2, domain='lawyer'), row(3, domain='lawyer')]
        s = G.summarize(rows, {r['id'] for r in rows})
        self.assertEqual((s['good'], s['good_domains'], s['done']), (3, ['hair-salon', 'lawyer'], False))
        rows.append(row(4, domain='restaurant'))
        s = G.summarize(rows, {r['id'] for r in rows})
        self.assertTrue(s['done'])

    def test_without_the_owners_word_a_build_is_not_good(self):
        s = G.summarize([row(1)], set())
        self.assertEqual((s['db_conditions_hold'], s['good']), (1, 0))
        self.assertIn('waiting for the owner', '\n'.join(G.lines(s)))


class TheTool(unittest.TestCase):
    def test_no_database_url_is_loud(self):
        with mock.patch.dict(os.environ, {'OMNI_DATABASE_URL': ''}), tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(G.main(['--out', f'{tmp}/o.json']), 2)
            self.assertFalse(Path(tmp, 'o.json').exists())

    def test_an_unreadable_database_is_loud_and_writes_nothing(self):
        def boom(*a, **k):
            raise ConnectionError('down')
        with mock.patch.dict(os.environ, {'OMNI_DATABASE_URL': 'postgres://x'}), tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(G.main(['--out', f'{tmp}/o.json'], connect=boom), 2)
            self.assertFalse(Path(tmp, 'o.json').exists())

    def test_reads_in_a_read_only_transaction(self):
        executed = []

        class Cur:
            description = [('id',), ('status',), ('created_at',), ('site_route',), ('repair_rounds',), ('skill_gates',)]

            def fetchall(self):
                r = row(1)
                return [tuple(r[k] for k in ('id', 'status', 'created_at', 'site_route', 'repair_rounds', 'skill_gates'))]

        class Conn:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql, params=None):
                executed.append(sql.strip().split()[0:3])
                return Cur()

            def rollback(self):
                executed.append(['ROLLBACK'])
        with mock.patch.dict(os.environ, {'OMNI_DATABASE_URL': 'postgres://x'}), tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'D.md').write_text(DECISIONS, encoding='utf-8')
            self.assertEqual(G.main(['--out', f'{tmp}/o.json', '--decisions', f'{tmp}/D.md'],
                                    connect=lambda *a, **k: Conn()), 0)
            out = json.loads(Path(tmp, 'o.json').read_text(encoding='utf-8'))
        self.assertEqual(executed[0], ['SET', 'TRANSACTION', 'READ'])
        self.assertEqual(executed[-1], ['ROLLBACK'])
        self.assertEqual(out['good'], 1)


if __name__ == '__main__':
    unittest.main()
