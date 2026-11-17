"""The classification corpus (the owner, 2026-11-17): 100 frozen requests with the product type a professional would
build, run on every change. One fixed word-matching bug was a symptom of a method -- matching inside words -- so the
check is a corpus, not three cases: a fourth bug of the same kind fails here before it reaches a customer.

The two rules the corpus guards each have their own test and negative control
(tests/test_a_word_inside_another_word.py): whole words with Hebrew prefixes, and a negated cue asks for nothing."""
import json
import unittest
from collections import Counter
from pathlib import Path

from omni_prod.intake.families import FAMILIES, classify_family

CORPUS = json.loads((Path(__file__).parent / 'fixtures' / 'classification_corpus.json').read_text(encoding='utf-8'))
ROWS = CORPUS['rows']


class TheCorpus(unittest.TestCase):
    def test_it_is_a_hundred_rows_with_known_types_and_real_requests_in_it(self):
        self.assertGreaterEqual(len(ROWS), 100)
        self.assertTrue(all(r['expected'] in FAMILIES for r in ROWS))
        self.assertTrue(all(r['source'] in ('production', 'claude') for r in ROWS))
        self.assertGreaterEqual(sum(r['source'] == 'production' for r in ROWS), 20)
        self.assertEqual(len({r['text'] for r in ROWS}), len(ROWS))                     # no duplicate request
        kinds = Counter(r['expected'] for r in ROWS)
        self.assertGreaterEqual(kinds['website'], 30)
        self.assertGreaterEqual(kinds['web_app'], 15)

    def test_every_request_gets_its_expected_type(self):
        wrong = [(r['text'][:70], r['expected'], classify_family(r['text'])) for r in ROWS
                 if classify_family(r['text']) != r['expected']]
        self.assertEqual(wrong, [], f'{len(wrong)} of {len(ROWS)} classified wrong')


if __name__ == '__main__':
    unittest.main()
