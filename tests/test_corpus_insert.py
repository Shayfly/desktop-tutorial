"""The corpus insert (migration 045's writer): never overwrites, holds out 20% by a rule that does not depend on order,
and refuses a malformed collection file. The collected file is the real one (restaurants, collected 2026-11-17)."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('corpus_insert_sql', ROOT / 'scripts' / 'corpus_insert_sql.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
COLLECTED = json.loads((ROOT / 'corpus' / 'collected' / 'restaurants.json').read_text(encoding='utf-8'))


class TheInsert(unittest.TestCase):
    def test_the_collected_file_meets_the_acceptance_shape(self):
        self.assertEqual(COLLECTED['category'], 'restaurants')
        self.assertEqual(len(COLLECTED['accepted']), 5)
        self.assertEqual(len({a['url'] for a in COLLECTED['accepted']}), 5)
        for a in COLLECTED['accepted']:
            self.assertTrue(a['phone'] or a['address'], a['url'])          # Israeli phone or address (DECISIONS 3)
            self.assertGreaterEqual(a['pages'], 3, a['url'])
            self.assertNotIn('wix', a['url'])
        self.assertTrue(all(r['reason'] for r in COLLECTED['rejected']))    # every rejection says why

    def test_a_page_already_collected_keeps_its_first_capture(self):
        self.assertIn('ON CONFLICT (url) DO NOTHING', C.statement(COLLECTED))
        self.assertNotIn('DO UPDATE', C.statement(COLLECTED))

    def test_the_holdout_is_a_rule_on_the_url(self):
        urls = [f'https://site{i}.co.il' for i in range(500)]
        share = sum(C.holdout(u) for u in urls) / len(urls)
        self.assertTrue(0.15 < share < 0.25, share)
        self.assertEqual([C.holdout(u) for u in urls], [C.holdout(u) for u in urls])
        reordered = dict(COLLECTED, accepted=list(reversed(COLLECTED['accepted'])))
        held = lambda c: {a['url'] for a in c['accepted'] if C.holdout(a['url'])}
        self.assertEqual(held(COLLECTED), held(reordered))

    def test_a_quote_cannot_break_the_statement(self):
        row = dict(COLLECTED['accepted'][0], business="ג'ורג' וושינגטון")
        sql = C.statement(dict(COLLECTED, accepted=[row]))
        self.assertIn("ג''ורג''", sql)

    def test_a_malformed_file_is_refused(self):
        with self.assertRaises(SystemExit):
            C.statement(dict(COLLECTED, accepted=[]))
        with self.assertRaises(SystemExit):
            C.statement(dict(COLLECTED, accepted=[{'url': 'ftp://x'}]))


if __name__ == '__main__':
    unittest.main()
