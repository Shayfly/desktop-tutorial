"""A syntax failure says which line, in words (rehearsal 44042316516, the butcher, 2026-11-17: the same
"tests/test_site.py:96 closing parenthesis ']' does not match opening parenthesis '('" came back after a pre-flight
fix and a repair round, and nothing said what line 96 was)."""
import unittest

from omni_prod import round_preflight as pf
from omni_prod import consistency_gate

BAD = 'def test_page():\n    html = get()\n    assert all(s in html for s in ("בקר טרי", "עוף"])\n'


class TheLineIsInTheMessage(unittest.TestCase):
    def test_pre_flight(self):
        found = pf.syntax_errors({'tests/test_site.py': BAD, 'app.py': 'x = 1\n'})
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]['file'], found[0]['line']), ('tests/test_site.py', 3))
        self.assertTrue(found[0]['message'].endswith(' -> `assert all(s in html for s in ("בקר טרי", "עוף"])`'),
                        found[0]['message'])
        self.assertIn('-> `assert all(', pf.syntax_failure(found)['message'])     # what the repairer is told

    def test_the_consistency_gate_says_the_same_line(self):
        failed = consistency_gate.failures(consistency_gate.scan({'tests/test_site.py': BAD}))
        self.assertEqual(len(failed), 1)
        self.assertIn('tests/test_site.py:3 Python syntax error', failed[0].message)
        self.assertIn('-> `assert all(s in html for s in ("בקר טרי", "עוף"])`', failed[0].message)

    def test_a_long_line_is_cut_and_the_cut_is_marked(self):
        text = 'x = (' + '"a", ' * 100 + ']\n'
        message = pf.syntax_errors({'a.py': text})[0]['message']
        shown = message.split(' -> `', 1)[1]
        self.assertTrue(shown.endswith('...`'))
        self.assertEqual(len(shown), pf.MAX_SOURCE_LINE + len('...`'))

    def test_no_line_no_tail(self):
        self.assertEqual(pf.source_line('a = 1\n', None), '')
        self.assertEqual(pf.source_line('a = 1\n', 7), '')
        self.assertEqual(pf.source_line('a = 1\n\n', 2), '')
        self.assertEqual(pf.source_line('a = 1\n', True and 0), '')

    def test_json_messages_are_unchanged(self):
        self.assertTrue(pf.syntax_errors({'a.json': '{'})[0]['message'].startswith('JSON error: '))


if __name__ == '__main__':
    unittest.main()
