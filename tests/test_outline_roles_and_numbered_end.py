"""The owner's numbered page structure (production 2026-11-19, bld_7da07ab0): the QA review failed the page for no
"פתיח" heading and for no "עיצוב" section -- "עיצוב: נקי ורציני..." is a style line after the list (the stored request
had lost its blank lines), and "פתיח" names the opening's role. The brief is the owner's message, verbatim."""
import os
import sys
import unittest

from omni_prod import page_outline as O
from omni_prod.product_spec import ProductSpec

sys.path.insert(0, os.path.dirname(__file__))
from test_long_request_is_not_a_question import BRIEF      # noqa: E402

SPEC = ProductSpec.from_dict({'title': 'T', 'summary': 'S', 'stack': ['python'],
                              'requirements': [{'id': 'R1', 'text': 'x', 'kind': 'functional', 'mandatory': True}],
                              'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'x'}]})
LISTED = ['פתיח', 'תחומי התמחות', 'על המשרד', 'איך זה עובד', 'שאלות נפוצות', 'צור קשר']


class TheNumberedListEnds(unittest.TestCase):
    def test_with_and_without_blank_lines_the_style_line_is_not_a_section(self):
        for text in (BRIEF, BRIEF.replace('\n\n', '\n')):
            self.assertEqual([t for t, _ in O.outline(text)], LISTED)

    def test_an_unnumbered_list_still_reads_every_line(self):
        text = 'מבנה הדף:\nהירו — דלת\nיתרונות — שישה\nשאלות נפוצות — חמש'
        self.assertEqual([t for t, _ in O.outline(text)], ['הירו', 'יתרונות', 'שאלות נפוצות'])


class TheOpeningNeedsNoHeading(unittest.TestCase):
    def test_the_acceptance_names_every_section_but_the_opening(self):
        spec = O.with_outline(SPEC, O.outline(BRIEF)).to_dict()
        acc = [a for a in spec['acceptance'] if a['id'] == O.REQUIREMENT][0]['text']
        self.assertNotIn('"פתיח"', acc)
        for t in LISTED[1:]:
            self.assertIn(f'"{t}"', acc)
        req = [r for r in spec['requirements'] if r['id'] == O.REQUIREMENT][0]['text']
        self.assertIn('needs no heading', req)
        self.assertIn('מייצגים עובדים', req)                # the opening's content is still required


if __name__ == '__main__':
    unittest.main()
