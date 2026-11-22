"""Warehouse 132 (the owner, 2026-11-22): the customer never needs the platform's words. One dictionary
(omni_prod.customer_words): the conversation agent is given it, the conversation-and-approval route holds zero platform
words, and every other customer text may only lose them (a ratchet against tests/fixtures/customer_words_baseline.json)."""
import collections
import json
import unittest
from pathlib import Path

from omni_prod import customer_words as W

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / 'tests' / 'fixtures' / 'customer_words_baseline.json').read_text(encoding='utf-8'))


class TheDictionary(unittest.TestCase):
    def test_a_word_is_found_with_its_hebrew_prefix_and_only_as_a_whole_word(self):
        self.assertEqual(W.machine_terms('שלב 2 — המפרט אושר'), ['מפרט'])
        self.assertEqual(W.machine_terms('הבנייה לא כלולה במסלול שלך'), ['מסלול'])
        self.assertEqual(W.machine_terms('נגמרו הקרדיטים'), ['קרדיטים'])
        self.assertEqual(W.machine_terms('מפרטים טכניים של המוצר, שרתים'), [])     # other words, not ours
        self.assertEqual(W.machine_terms('אישרתם מה שהבנתי'), [])

    def test_the_agent_is_told_every_word(self):
        from omni_prod.intake.interpreter import SYSTEM
        for term, _ in W.HE + W.EN:
            if not term.startswith('ה'):
                self.assertIn(f'"{term}"', SYSTEM, term)


class TheCustomerText(unittest.TestCase):
    def counts(self, path):
        return collections.Counter(t for _, t, _ in W.scan(path, root=ROOT))

    def test_the_conversation_route_holds_no_platform_word(self):
        for path in W.CONVERSATION:
            with self.subTest(path):
                self.assertEqual([(n, t, s[:60]) for n, t, s in W.scan(path, root=ROOT)], [])

    def test_no_other_customer_text_gains_a_platform_word(self):
        for path in W.CUSTOMER_TEXT:
            allowed = BASELINE['counts'].get(path, {})
            for term, n in self.counts(path).items():
                with self.subTest(path=path, term=term):
                    self.assertLessEqual(n, allowed.get(term, 0))

    def test_the_baseline_lists_no_conversation_file(self):
        self.assertFalse(set(BASELINE['counts']) & set(W.CONVERSATION))

    def test_a_planted_word_is_caught(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'omni_prod' / 'intake').mkdir(parents=True)
            (Path(tmp) / 'omni_prod' / 'intake' / 'venice.py').write_text(
                "T = {'x': 'אשרו את המפרט', 'y': 'עלות {credits} קרדיטים'}\n", encoding='utf-8')
            found = sorted(t for _, t, _ in W.scan('omni_prod/intake/venice.py', root=tmp))
            self.assertEqual(found, ['מפרט', 'קרדיטים'])


if __name__ == '__main__':
    unittest.main()
