"""2026-11-21 (rehearsal run 44943528189, a hair salon whose request asked for testimonials and gave none): the
generator was told sample testimonials may carry a "(לדוגמה)" label, the reviewer's checklist forbade any named
testimonial the request did not give, so three repair rounds could not converge and the build FAILED. The generator,
the static gate and the reviewer now read one rule: a requested-but-unsupplied reviews section is left out; a sample
carries "(לדוגמה)" on its heading and names no person. Mutations: tests/negative_controls/testimonials_one_rule.json."""
import unittest

from omni_prod import skills_runtime as S
from omni_prod.fact_canon import build_canon

COPY = next(v for v in vars(S).values() if getattr(v, 'key', None) == 'skill.copy_quality')
REQUEST = 'אתר לסלון מספרה בחיפה: רשימת שירותים ומחירים, המלצות של לקוחות, וכפתור לתיאום תור.'


def page(reviews: str) -> str:
    return ('<!doctype html><html lang="he" dir="rtl"><head><title>סלון</title></head><body><main>'
            '<h1>סלון בחיפה</h1><h2>שירותים</h2><p>תספורת</p>' + reviews + '</main></body></html>')


def blocking_copy(html: str) -> list[str]:
    ctx = {'request': REQUEST, 'rendered_pages': {'/': html, 'assets': ''}, 'canon': build_canon(REQUEST)}
    repo = {'page.py': 'HTML = """' + html + '"""', 'app.py': 'pass'}
    return [f.problem for f in S.static_findings(repo, ctx) if f.skill == 'skill.copy_quality' and f.severity == 'blocking']


class OneRule(unittest.TestCase):
    def test_the_generator_is_told_to_leave_the_section_out_or_label_it_without_names(self):
        g = COPY.guidance
        self.assertIn('leave that section out', g)
        self.assertIn('"(לדוגמה)"', g)
        self.assertIn('names no person', g)

    def test_the_reviewer_checklist_says_the_same(self):
        rule = next(c for c in COPY.checklist if 'testimonial' in c)
        self.assertIn('"(לדוגמה)"', rule)
        self.assertIn('names no person', rule)
        self.assertNotIn('No phone number, address or named testimonial that the request did not give.', COPY.checklist)

    def test_the_static_gate_accepts_what_both_texts_allow(self):
        # a labelled sample without names passes the static gate, so the path both texts describe is open
        sample = '<h2>המלצות (לדוגמה)</h2><blockquote>“שירות מצוין” — לקוחה</blockquote><blockquote>“תוצאה מדויקת” — לקוח</blockquote>'
        self.assertEqual(blocking_copy(page(sample)), [])
        self.assertEqual(blocking_copy(page('')), [])                      # the section left out passes too

    def test_unlabelled_invented_testimonials_still_block(self):
        invented = '<h2>המלצות</h2><blockquote>“שירות מצוין” — יעל</blockquote><blockquote>“תוצאה מדויקת” — דני</blockquote>'
        self.assertTrue(any('testimonials' in p for p in blocking_copy(page(invented))))


if __name__ == '__main__':
    unittest.main()
