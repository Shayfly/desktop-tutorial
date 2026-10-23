"""H1 deterministic tail classes. No external model calls."""
import unittest
from omni_prod.model_gateway import parse_model_json

class TailClassification(unittest.TestCase):
    def verify(self, raw, status, verdict):
        obj, diag = parse_model_json(raw)
        self.assertEqual(obj, {'files': []})
        self.assertEqual(diag['tail_status'], status)
        self.assertEqual(diag['verdict'], verdict)
        self.assertEqual(diag['tail'], raw.strip()[len('{"files": []}'):])
        self.assertEqual(diag['trailing_chars'], len(diag['tail']))
        self.assertEqual(diag['trailing_starts'], diag['tail'][:80])
        return diag

    def test_benign_empty(self):
        self.verify('{"files": []}  ', 'benign_empty', 'accepted')

    def test_benign_prose(self):
        self.verify('{"files": []} AND ALSO', 'benign_prose', 'accepted_with_unexplained_tail')

    def test_benign_second_object_match(self):
        self.verify('{"files": []} {"files": []}', 'benign_second_object_match', 'accepted_with_unexplained_tail')

    def test_conflict_second_object_is_flagged(self):
        d = self.verify('{"files": []} {"files": [1]}', 'conflict_second_object', 'accepted_with_conflict')
        self.assertTrue(d['tail_conflict'])

    def test_malformed_tail_is_flagged(self):
        d = self.verify('{"files": []} {"files":', 'malformed_tail', 'accepted_with_conflict')
        self.assertTrue(d['tail_conflict'])

    def test_negative_tail_not_silently_eaten(self):
        d = self.verify('{"files": []} SUSPICIOUS', 'benign_prose', 'accepted_with_unexplained_tail')
        self.assertEqual(d['tail'], ' SUSPICIOUS')

if __name__ == '__main__':
    unittest.main()
