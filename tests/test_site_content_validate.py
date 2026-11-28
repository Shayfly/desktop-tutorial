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

    def problems(self, doc, sheet=None, **kw):
        return V.validate(doc, sheet or self.sheet, self.offered, TITLES, claim_mode=kw.get('claim_mode', 'warn'))

    def without(self, *facts):
        """The production sheet with these facts not given (the customer gave no e-mail, no WhatsApp...)."""
        sheet = copy.copy(self.sheet)
        for f in facts:
            setattr(sheet, f, None)
        return sheet

    def doc(self):
        return copy.deepcopy(FIXTURE['scripted_content'])

    def codes(self, doc, sheet=None, **kw):
        return {(p.path, p.code) for p in self.problems(doc, sheet=sheet, **kw)}

    def test_the_owners_brief_passes_clean(self):
        self.assertEqual(self.problems(self.doc()), [])

    def test_every_code_has_a_failing_document(self):
        cases = {}

        def case(code, path, mutate, sheet=None, **kw):
            doc = self.doc()
            mutate(doc)
            cases[code] = (path, self.codes(doc, sheet=sheet, **kw))

        sec = lambda d: d['sections']                                                        # noqa: E731
        case('SCHEMA_SHAPE', 'sections.services.icon', lambda d: sec(d)['services'].update(icon='⚖'))
        case('LAYOUT_UNKNOWN', 'layout.hero', lambda d: d['layout'].update(hero='carousel'))
        case('TOO_LONG', 'sections.hero.cta', lambda d: sec(d)['hero'].update(cta='לתיאום פגישת ייעוץ ' * 3))
        case('TOO_FEW', 'sections.faq.items', lambda d: sec(d)['faq'].update(items=sec(d)['faq']['items'][:1]))
        case('TOO_MANY', 'sections.process.steps', lambda d: sec(d)['process'].update(     # 15: past the 12 steps
            steps=sec(d)['process']['steps'] * 5))                                          # allowed on 2026-11-26
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
        case('PRICE_NOT_SHOWN', 'sections', lambda d: (sec(d)['hero'].pop('note'), sec(d)['faq']['items'][0].update(
            a='העלות נקבעת לפי סוג התיק.')))
        case('PRICE_CONTEXT', 'sections.hero.note', lambda d: sec(d)['hero'].update(note='ליווי תיק מלא: @price:1'))
        case('PRICE_CONTRADICTED', 'sections.faq.items[1].a', lambda d: sec(d)['faq']['items'][1].update(
            a='פגישת הייעוץ הראשונה ללא עלות.'))
        case('CHANNEL_NOT_GIVEN', 'sections.about.paragraphs[0]', lambda d: sec(d)['about']['paragraphs'].__setitem__(
            0, 'כתבו לנו במייל, ונחזור אליכם.'), sheet=self.without('email'))
        case('UNSUPPORTED_DETAIL', 'sections.about.paragraphs[0]', lambda d: sec(d)['about']['paragraphs'].__setitem__(
            0, 'המשרד פועל גם בירושלים ובחיפה.'))
        case('NAME_NOT_GIVEN', 'name', lambda d: d.update(name='כהן ושות׳ עורכי דין ונוטריונים'))
        case('PLACEHOLDER', 'sections.contact.lead', lambda d: sec(d)['contact'].update(lead='כתבו לנו ל«דוא״ל»'))
        case('UNVERIFIABLE_CLAIM', 'sections.hero.lead', lambda d: sec(d)['hero'].update(
            lead='המשרד המוביל בדיני עבודה, משיחת הייעוץ ועד סיום ההליך.'))
        # visual plan S3: the customer's items all have pictures, and no card names one
        pictured = copy.copy(self.sheet)
        pictured.items = [{'id': '@item:1', 'text': 'פיטורים'}, {'id': '@item:2', 'text': 'הטרדה'}]
        pictured.item_images = {i['id']: {'src': f'148ai-asset://image/{n}', 'alt': i['text']} for n, i in enumerate(pictured.items, 1)}
        case('ITEM_PICTURE_UNPLACED', 'sections.services.items', lambda d: None, sheet=pictured)
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

    def test_a_customer_number_counts_only_what_the_customer_counted(self):
        def at(path, mutate):
            doc = self.doc()
            mutate(doc)
            return [p.why for p in self.problems(doc) if p.path == path and p.code == 'INVENTED_NUMBER']
        sec = lambda d: d['sections']                                                        # noqa: E731
        para = 'sections.about.paragraphs[1]'
        cases = {
            # the price 250 ("250 ₪") is not a number the copy may use, and 3 counted lawyers, not years
            'price as years': ('sections.hero.panel_figure.value', lambda d: sec(d)['hero']['panel_figure'].update(
                value='250', caption='שנות ניסיון בדיני עבודה')),
            'lawyers as years': ('sections.hero.panel_figure.value', lambda d: sec(d)['hero']['panel_figure'].update(
                value='3', caption='שנות ניסיון')),
            '3 decades': (para, lambda d: sec(d)['about']['paragraphs'].__setitem__(
                1, 'ניסיון של 3 עשורים בדיני עבודה.')),
            '250 cases won': (para, lambda d: sec(d)['about']['paragraphs'].__setitem__(
                1, 'יותר מ-250 תיקים שהסתיימו בזכייה.')),
            'a year as clients': (para, lambda d: sec(d)['about']['paragraphs'].__setitem__(1, 'יותר מ-2008 לקוחות.')),
            'seniority 250 years': ('sections.about.facts[0].value', lambda d: sec(d)['about'].update(
                facts=[{'label': 'ותק', 'value': '250 שנה'}])),
        }
        for label, (path, mutate) in cases.items():
            with self.subTest(label):
                self.assertTrue(at(path, mutate), label)
        doc = self.doc()
        sec(doc)['about']['paragraphs'][1] = 'שלושה עורכי דין, יותר מ-1,500 תיקים, ומאז 2008 בדיני עבודה.'
        sec(doc)['about']['facts'] = [{'label': 'שנת הקמה', 'value': 'מאז 2008'}]
        self.assertEqual(self.problems(doc), [])

    def test_a_number_written_in_words_is_a_number(self):
        doc = self.doc()
        doc['sections']['about']['paragraphs'][1] = 'שישה עורכי דין, עשרים שנות ניסיון ומאות לקוחות מרוצים.'
        found = [p.why for p in self.problems(doc) if p.code == 'INVENTED_NUMBER']
        self.assertEqual(found, ['number(s) the customer never wrote: שישה, עשרים, ומאות'])
        # the section's own count in its title is the page's ("שלושה שלבים" over three steps), and "אחד" is a word
        self.assertEqual(self.doc()['sections']['process']['title'], 'שלושה שלבים, ליווי אחד')
        doc = self.doc()
        doc['sections']['services']['title'] = 'ארבעה תחומי ייצוג'
        self.assertEqual(self.problems(doc), [])
        doc['sections']['services']['title'] = 'חמישה תחומי ייצוג'
        self.assertIn(('sections.services.title', 'INVENTED_NUMBER'), self.codes(doc))

    def test_facts_written_as_words_are_caught(self):
        """The reviewer's combined document (factlens a7/a1/a8): every fact written as words is refused (block) or,
        where the pattern has real false positives, recorded (warn, SITE_CLAIMS calibrating)."""
        block = {
            'שישה עורכי דין ליוו אתכם.': 'INVENTED_NUMBER',
            'עשרים שנות ניסיון בדיני עבודה.': 'INVENTED_NUMBER',
            'מאות לקוחות מרוצים בכל הארץ.': 'INVENTED_NUMBER',
            'זמינים בכל שעות היממה, כל ימות השבוע.': 'FACT_IN_COPY',
            'פתוחים גם בשבת לפגישות דחופות.': 'FACT_IN_COPY',
            'דירוג ★★★★★ מלקוחותינו.': 'INVENTED_COUNT',
            'פגישת הייעוץ הראשונה ללא עלות.': 'PRICE_CONTRADICTED',
        }
        warn = {
            '"ליווי מקצועי ואנושי לאורך כל הדרך", אמרה לנו לקוחה.': 'quotation',
            'עו״ד דנה כהן מובילה את תחום הפיטורים.': 'person',
            'בראש המשרד עומדת שופטת לשעבר.': 'credential',
            'יש לנו סניפים בירושלים ובחיפה.': 'place',
            'פגישות גם ביום שישי בבוקר.': 'day',
        }
        for text, code in block.items():
            with self.subTest(text):
                doc = self.doc()
                doc['sections']['about']['paragraphs'][0] = text
                found = [p for p in self.problems(doc) if p.path == 'sections.about.paragraphs[0]']
                self.assertIn((code, 'block'), {(p.code, p.severity) for p in found})
        for text, what in warn.items():
            with self.subTest(text):
                doc = self.doc()
                doc['sections']['about']['paragraphs'][0] = text
                found = [p for p in self.problems(doc) if p.code == 'UNSUPPORTED_DETAIL']
                self.assertEqual([p.severity for p in found], ['warn'])
                self.assertIn(f'a {what}', found[0].why)
                self.assertEqual([p.severity for p in self.problems(doc, claim_mode='block')
                                  if p.code == 'UNSUPPORTED_DETAIL'], ['block'])
        # WhatsApp in copy while the customer gave no WhatsApp (factlens a8)
        self.assertIn(('sections.contact.lead', 'CHANNEL_NOT_GIVEN'), self.codes(self.doc(), sheet=self.without('whatsapp')))
        self.assertEqual(self.problems(self.doc()), [])                     # with the customer's WhatsApp it passes

    def test_every_page_price_is_shown_next_to_its_own_label(self):
        self.assertEqual([(p['id'], p['words']) for p in self.sheet.prices], [('@price:1', ['ייעוץ', 'ראשון'])])
        doc = self.doc()
        doc['sections']['faq']['items'][0]['a'] = 'זה עולה @price:1.'           # the question carries the label
        self.assertEqual(self.problems(doc), [])
        doc['sections']['faq']['items'][2]['a'] = 'ליווי תיק מלא עולה @price:1.'
        self.assertIn(('sections.faq.items[2].a', 'PRICE_CONTEXT'), self.codes(doc))

    def test_a_build_budget_is_never_a_page_price_and_the_customers_own_free_is_theirs(self):
        prompt = FIXTURE['prompt']
        end = prompt.index('--- Approved project brief')
        prompt = prompt[:end] + 'התקציב שלי לבניית האתר הוא עד 3,000 ₪. ייעוץ טלפוני קצר חינם.\n' + prompt[end:]
        sheet = Fx.fact_sheet(prompt)
        self.assertEqual([p['span'] for p in sheet.prices], ['250 ₪'])
        self.assertEqual([p['span'] for p in sheet.withheld_prices], ['3,000 ₪'])
        seen = json.dumps(sheet.for_model(), ensure_ascii=False)
        self.assertNotIn('3,000', seen)
        self.assertNotIn('3000', sheet.allowed_numbers())
        doc = self.doc()
        doc['sections']['faq']['items'][1]['a'] = 'ייעוץ טלפוני קצר חינם, ובפגישה נעריך את לוח הזמנים.'
        self.assertEqual(V.validate(doc, sheet, self.offered, TITLES, claim_mode='warn'), [])

    def test_with_no_declared_name_the_name_is_one_the_customer_quoted(self):
        self.assertIsNone(self.sheet.name)
        self.assertEqual(self.sheet.name_candidates, ['כהן ושות׳ – דיני עבודה'])
        for name in ('כהן ושות׳', 'כהן ושות׳ – דיני עבודה'):
            doc = self.doc()
            doc['name'] = name
            self.assertEqual(self.problems(doc), [], name)
        # part of the customer's text, not their business name: a city, a button text quoted in the outline
        for name in ('תל אביב', 'לתיאום פגישת ייעוץ', 'דיני עבודה', 'מייצגים עובדים ומעסיקים בדיני עבודה מאז 2008'):
            doc = self.doc()
            doc['name'] = name
            with self.subTest(name):
                self.assertIn(('name', 'NAME_NOT_GIVEN'), self.codes(doc))

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
