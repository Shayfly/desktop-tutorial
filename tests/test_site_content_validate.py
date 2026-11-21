"""The content document is refused before rendering for every rule the route states (site_content/validate.py): each
code has a document that fails with exactly that code at the path that broke it, and the owner's brief with its
scripted content passes clean. The sheet is the production brief's (bld_b0eb47a5, read-only, fingerprint asserted in
test_site_content_render.py)."""
import copy
import json
import unittest
from pathlib import Path

from omni_prod.section_library import DIRECTIONS
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import schema as K
from omni_prod.site_content import validate as V

FIXTURE = json.loads((Path(__file__).resolve().parent / 'fixtures' / 'site_content_bld_b0eb47a5.json')
                     .read_text(encoding='utf-8'))
TITLES = {'services': 'תחומי התמחות', 'about': 'על המשרד', 'process': 'איך זה עובד', 'faq': 'שאלות נפוצות',
          'contact': 'צור קשר'}
ORDER = ['hero', 'services', 'about', 'process', 'faq', 'contact']


class TheValidator(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.sheet = Fx.fact_sheet(FIXTURE['prompt'])
        cls.offered, _ = K.offered_sections(cls.sheet, DIRECTIONS['palettes']['counsel'], ORDER, TITLES)

    def problems(self, doc, **kw):
        return V.validate(doc, self.sheet, self.offered, TITLES, claim_mode=kw.get('claim_mode', 'warn'))

    def doc(self):
        return copy.deepcopy(FIXTURE['scripted_content'])

    def codes(self, doc, **kw):
        return {(p.path, p.code) for p in self.problems(doc, **kw)}

    def test_the_owners_brief_passes_clean(self):
        self.assertEqual(self.problems(self.doc()), [])

    def test_every_code_has_a_failing_document(self):
        cases = {}

        def case(code, path, mutate, **kw):
            doc = self.doc()
            mutate(doc)
            cases[code] = (path, self.codes(doc, **kw))

        sec = lambda d: d['sections']                                                        # noqa: E731
        case('SCHEMA_SHAPE', 'sections.services.icon', lambda d: sec(d)['services'].update(icon='⚖'))
        case('LAYOUT_UNKNOWN', 'layout.hero', lambda d: d['layout'].update(hero='carousel'))
        case('TOO_LONG', 'sections.hero.cta', lambda d: sec(d)['hero'].update(cta='לתיאום פגישת ייעוץ ' * 3))
        case('TOO_FEW', 'sections.faq.items', lambda d: sec(d)['faq'].update(items=sec(d)['faq']['items'][:1]))
        case('TOO_MANY', 'sections.process.steps', lambda d: sec(d)['process'].update(
            steps=sec(d)['process']['steps'] * 3))
        case('EMPTY_TEXT', 'sections.hero.lead', lambda d: sec(d)['hero'].update(lead='  '))
        case('NOT_HEBREW', 'sections.services.items[0].desc', lambda d: sec(d)['services']['items'][0].update(
            desc='Unfair dismissal claims.'))
        case('FACT_IN_COPY', 'sections.contact.lead', lambda d: sec(d)['contact'].update(
            lead='התקשרו אלינו: 03-5551234'))
        case('INVENTED_NUMBER', 'sections.about.paragraphs[1]', lambda d: sec(d)['about']['paragraphs'].__setitem__(
            1, 'יותר מ-15 שנות ניסיון בדיני עבודה.'))
        case('INVENTED_COUNT', 'sections.about.paragraphs[0]', lambda d: sec(d)['about']['paragraphs'].__setitem__(
            0, 'מעל 3 ביקורות מלקוחות.'))
        case('REF_UNKNOWN', 'sections.hero.note', lambda d: sec(d)['hero'].update(note='ייעוץ ראשון: @price:7'))
        case('REVIEW_TEXT_WRITTEN', 'sections.about.paragraphs[0]', lambda d: sec(d)['about']['paragraphs'].__setitem__(
            0, '"ליווי מקצועי ואנושי לאורך כל הדרך" – דנה'))
        case('PRICE_NOT_GIVEN', 'sections.faq.items[0].a', lambda d: sec(d)['faq']['items'][0].update(
            a='פגישת ייעוץ ראשונה עולה 250 ש"ח.'))
        case('NAME_NOT_GIVEN', 'name', lambda d: d.update(name='כהן ושות׳ עורכי דין ונוטריונים'))
        case('PLACEHOLDER', 'sections.contact.lead', lambda d: sec(d)['contact'].update(lead='כתבו לנו ל«דוא״ל»'))
        case('UNVERIFIABLE_CLAIM', 'sections.hero.lead', lambda d: sec(d)['hero'].update(
            lead='המשרד המוביל בדיני עבודה, משיחת הייעוץ ועד סיום ההליך.'))
        self.assertEqual(set(cases), set(V.CODES))                    # a code with no failing document fails here
        for code, (path, found) in cases.items():
            with self.subTest(code=code):
                self.assertIn((path, code), found)

    def test_a_model_written_phone_is_refused_wherever_it_is(self):
        doc = self.doc()
        doc['sections']['faq']['items'][2]['a'] = 'אפשר לתאם בטלפון 050-5551234.'
        self.assertIn(('sections.faq.items[2].a', 'FACT_IN_COPY'), self.codes(doc))
        doc = self.doc()
        doc['description'] = 'משרד עורכי דין בדרך מנחם בגין 132, תל אביב.'
        self.assertIn(('description', 'FACT_IN_COPY'), self.codes(doc))

    def test_a_number_the_customer_never_wrote_is_refused_even_as_a_stat(self):
        doc = self.doc()
        doc['sections']['hero']['panel_figure']['value'] = '+2,000'
        self.assertIn(('sections.hero.panel_figure.value', 'INVENTED_NUMBER'), self.codes(doc))
        doc = self.doc()
        doc['sections']['hero']['lead'] = 'זמינים 24/7 לכל שאלה בדיני עבודה.'
        self.assertIn(('sections.hero.lead', 'INVENTED_NUMBER'), self.codes(doc))

    def test_the_customers_numbers_as_written_pass(self):
        doc = self.doc()
        doc['sections']['about']['paragraphs'][1] = 'עד היום ליווינו יותר מ-1,500 תיקים, ואנחנו 3 עורכי דין.'
        self.assertEqual(self.problems(doc), [])

    def test_the_claim_check_warns_while_it_is_calibrating_and_blocks_when_switched(self):
        doc = self.doc()
        doc['sections']['hero']['lead'] = 'המשרד המוביל בדיני עבודה, משיחת הייעוץ ועד סיום ההליך.'
        warn = [p for p in self.problems(doc) if p.code == 'UNVERIFIABLE_CLAIM']
        self.assertEqual([p.severity for p in warn], ['warn'])
        self.assertEqual(V.blocking(self.problems(doc)), [])
        self.assertEqual([p.severity for p in self.problems(doc, claim_mode='block') if p.code == 'UNVERIFIABLE_CLAIM'],
                         ['block'])

    def test_a_section_that_was_not_offered_is_refused(self):
        doc = self.doc()
        doc['sections']['testimonials'] = {'title': 'מה אומרים', 'nav': 'המלצות', 'items': ['@review:1']}
        self.assertIn(('sections.testimonials', 'SCHEMA_SHAPE'), self.codes(doc))

    def test_with_the_customers_outline_the_eyebrow_is_the_platforms(self):
        doc = self.doc()
        doc['sections']['services']['eyebrow'] = 'מה אנחנו עושים'
        self.assertIn(('sections.services.eyebrow', 'SCHEMA_SHAPE'), self.codes(doc))


if __name__ == '__main__':
    unittest.main()
