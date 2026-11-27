"""Warehouse 123 (released by the owner 2026-11-27, inbox/004): the page-type typology and its skeletons.

A website is one of eight page types. The registry (omni_prod/output_profile/page_types.json) is the output profile's own
data; the detector maps an APPROVED prompt to a type without guessing; section_library consumes each type's skeleton (the
sections, their order, the required ones) and the gates read its threshold table. Every test here crosses the real code:
the real detector on real production brief shapes (tests/fixtures/page_type_corpus.json, whose production rows are the
first messages of real projects and the approved prompts of real builds), the real section library rendering the owner's
own law-firm page, the real threshold measure on that rendered page.
"""
import copy
import json
import unittest
from pathlib import Path

from omni_prod import section_library as L
from omni_prod.intake.families import EXECUTABLE
from omni_prod.output_profile import PROFILES, ProfileMissing, detect_page_type
from omni_prod.output_profile import page_types as PT
from omni_prod.section_library import demo_law_firm as D

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / 'tests' / 'fixtures'
CORPUS = json.loads((FIX / 'page_type_corpus.json').read_text(encoding='utf-8'))['rows']
EIGHT = ('business', 'portfolio', 'event', 'community', 'documentation', 'product', 'personal', 'landing')


def text_of(row) -> str:
    if 'text' in row:
        return row['text']
    value = json.loads((FIX / row['fixture']).read_text(encoding='utf-8'))
    for k in row['key']:
        value = value[k]
    return value


class RegistryTruth(unittest.TestCase):
    def test_the_typology_is_exactly_the_eight_types_the_owner_named(self):
        self.assertEqual(PT.TYPES, EIGHT)

    def test_every_skeleton_is_a_seed_of_library_sections_only(self):
        keys = [k for k, _ in L.ORDER]
        for name in PT.TYPES:
            with self.subTest(name):
                sk = PT.skeleton(name)
                self.assertEqual(sk['source'], 'seed')           # until a corpus run (item 120) replaces it
                self.assertEqual(sk['sections'][0], 'hero')
                self.assertTrue(set(sk['sections']) <= set(keys))
                self.assertTrue(set(sk['required_sections']) <= set(sk['sections']))
                self.assertFalse(set(sk['not_in_library']) & set(keys))
                self.assertEqual(set(sk['thresholds']), set(PT.METRICS))
                self.assertEqual(sk['page_type'], name)

    def test_the_data_check_refuses_every_malformed_entry(self):
        def mutate(fn):
            data = copy.deepcopy(PT._DATA)
            fn(data['types'])
            return data
        cases = {
            'seven types': lambda t: t.pop('landing'),
            'unknown source': lambda t: t['event'].update(source='guess'),
            'corpus without pages': lambda t: t['event'].update(source='corpus'),
            'corpus with two pages': lambda t: t['event'].update(source='corpus', corpus_pages=['a', 'b']),
            'hero not first': lambda t: t['event'].update(sections=['about', 'hero']),
            'repeated section': lambda t: t['event'].update(sections=['hero', 'about', 'about']),
            'required outside sections': lambda t: t['event'].update(required_sections=['gallery']),
            'inverted threshold': lambda t: t['event']['thresholds'].update(images=[9, 1]),
            'missing metric': lambda t: t['event']['thresholds'].pop('ctas'),
            'no strong cue': lambda t: t['event']['cues'].update({'3': []}),
            'empty label': lambda t: t['event'].update(label_en=' '),
        }
        for what, fn in cases.items():
            with self.subTest(what), self.assertRaises(RuntimeError):
                PT.check(mutate(fn))
        PT.check(copy.deepcopy(PT._DATA))                         # the real data passes
        ok = mutate(lambda t: t['event'].update(source='corpus', corpus_pages=list('abcde')))
        PT.check(ok)                                              # five pages is a corpus skeleton

    def test_an_unknown_type_or_none_raises_never_defaults(self):
        for bad in (None, '', 'hologram', 'Business', 'website'):
            with self.subTest(bad), self.assertRaises(PT.UnknownPageType):
                PT.skeleton(bad)

    def test_the_skeleton_is_a_copy(self):
        sk = PT.skeleton('business')
        sk['sections'].append('x')
        sk['thresholds']['sections'][0] = 99
        self.assertNotIn('x', PT.skeleton('business')['sections'])
        self.assertNotEqual(PT.thresholds('business')['sections'][0], 99)

    def test_the_output_profile_carries_the_types_for_a_page_and_none_for_a_tool(self):
        self.assertEqual(PROFILES['website'].page_types, EIGHT)
        self.assertEqual(PROFILES['web_app'].page_types, ())
        self.assertEqual(set(PROFILES), set(EXECUTABLE))
        self.assertEqual(PROFILES['website'].to_dict()['page_types'], EIGHT)


class Detector(unittest.TestCase):
    def test_every_corpus_row_gets_its_label_from_the_real_detector(self):
        self.assertGreaterEqual(sum(r['source'] == 'production' for r in CORPUS), 30)
        for row in CORPUS:
            with self.subTest(text_of(row)[:60].replace('\n', ' ')):
                got = detect_page_type(row['family'], text_of(row))
                self.assertEqual((got.page_type, got.found), (row['page_type'], row['found']), got.to_dict())

    def test_all_eight_types_are_named_by_some_row_and_production_names_business_and_community(self):
        named = {r['page_type'] for r in CORPUS if r['page_type']}
        self.assertEqual(named, set(EIGHT))
        production = {r['page_type'] for r in CORPUS if r['source'] == 'production' and r['page_type']}
        self.assertEqual(production, {'business', 'community'})        # the other six: no production row yet

    def test_the_real_law_firm_brief_is_a_business_and_its_cases_are_not_a_portfolio(self):
        prompt = text_of({'fixture': 'site_content_bld_b0eb47a5.json', 'key': ['prompt']})
        got = detect_page_type('website', prompt)
        self.assertEqual((got.page_type, got.found), ('business', 'named'))
        self.assertEqual(got.scores['portfolio'], 0)               # "1,500 תיקים" is not a "תיק עבודות"

    def test_a_business_that_says_landing_page_is_a_business_the_landing_word_is_a_form_not_a_goal(self):
        # production, the cafe and the locksmith: "דף נחיתה לבית קפה", "דף נחיתה לעסק מנעולנות"
        for text in ('דף נחיתה לבית קפה קטן, עם שעות פתיחה וכפתור הזמנת שולחן', 'דף נחיתה למאפייה שלי בחיפה'):
            with self.subTest(text):
                got = PT.detect_text(text)
                self.assertEqual(got.page_type, 'business')
                self.assertGreater(got.scores['landing'], 0)
        self.assertEqual(PT.detect_text('דף נחיתה לסדנת קרמיקה').page_type, 'landing')

    def test_no_signal_is_none_and_never_a_default(self):
        for text in ('אתר', '', 'בלוג על בישול טבעוני', 'שלום'):
            with self.subTest(text):
                got = PT.detect_text(text)
                self.assertEqual((got.page_type, got.found), (None, 'none'))

    def test_a_shared_top_score_is_a_tie_with_its_candidates(self):
        got = PT.detect_text('אתר לחנות וגם הרצאה')
        self.assertEqual((got.page_type, got.found), (None, 'tie'))
        self.assertEqual(got.candidates, ('business', 'event'))

    def test_one_weak_cue_is_not_enough(self):
        got = PT.detect_text('אתר עם תאריך')
        self.assertEqual((got.page_type, got.found), (None, 'none'))
        self.assertEqual(got.scores['event'], 1)

    def test_weak_cues_are_capped(self):
        got = PT.detect_text('שעות פתיחה כתובת רחוב טלפון וואטסאפ משלוחים שירות')
        self.assertEqual(got.scores['business'], PT._DATA['weak_cap'])

    def test_a_word_inside_another_word_is_not_a_cue_and_a_hebrew_prefix_is(self):
        self.assertEqual(PT.detect_text('אתר למאמן כושר').scores['portfolio'], 0)      # "מאמן" is not "אמן"
        self.assertEqual(PT.detect_text('אתר לעסק שלי').page_type, 'business')          # ל + עסק
        self.assertEqual(PT.detect_text('אתר לקייטרינג לאירועים').scores['event'], 0)   # a caterer is not an event

    def test_a_negated_cue_does_not_count(self):
        self.assertEqual(PT.detect_text('בלי תיק עבודות, אתר לעסק שלי').page_type, 'business')
        self.assertEqual(PT.detect_text('אתר לעסק שלי, בלי תיק עבודות').scores['portfolio'], 0)
        self.assertEqual(PT.detect_text('אתר לצלמת עם תיק עבודות').page_type, 'portfolio')

    def test_a_longer_cue_counts_once_not_with_the_cue_inside_it(self):
        self.assertEqual(PT.detect_text('בית קפה').scores['business'], 3)                 # not 3 + the cue "קפה"
        self.assertEqual(PT.detect_text('משרד עורכי דין').scores['business'], 3)

    def test_it_reads_the_customers_words_and_never_148ais_wording_of_the_brief(self):
        prompt = text_of({'fixture': 'site_content_bld_b0eb47a5.json', 'key': ['prompt']})
        noise = '\nNotes: a conference landing page for a personal page portfolio community documentation product'
        self.assertEqual(PT.detect(prompt + noise).to_dict(), PT.detect(prompt).to_dict())
        self.assertNotEqual(PT.detect_text(noise).page_type, 'business')                  # the same words, said by the customer

    def test_it_is_deterministic(self):
        for row in CORPUS:
            text = text_of(row)
            self.assertEqual(PT.detect(text).to_dict(), PT.detect(text).to_dict())

    def test_the_stable_key_is_page_type_and_is_a_type_or_none(self):
        for row in CORPUS:
            got = detect_page_type(row['family'], text_of(row)).to_dict()
            self.assertIn('page_type', got)
            self.assertIn(got['page_type'], (None,) + EIGHT)
            self.assertIn(got['found'], PT.FOUND)

    def test_a_tool_or_an_unsupported_family_has_no_page_type_and_an_unknown_one_raises(self):
        for family in ('web_app', 'game', 'media'):
            with self.subTest(family):
                self.assertEqual(detect_page_type(family, 'אתר לעסק שלי').found, 'not_a_page')
        for bad in ('hologram', '', 'WEBSITE'):
            with self.subTest(bad), self.assertRaises(ProfileMissing):
                detect_page_type(bad, 'אתר לעסק שלי')


class Thresholds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = D.build()[0]

    def test_the_measure_reads_the_rendered_page(self):
        got = PT.measure(self.doc)
        self.assertEqual(got['h1'], 1)
        self.assertEqual(got['images'], 0)
        self.assertEqual(got['sections'], 8)
        self.assertEqual(got['ctas'], 5)
        self.assertGreater(got['text_chars'], 1500)
        with_images = self.doc.replace('</main>', '<img src="a" alt="a"><img src="b" alt="b"></main>')
        self.assertEqual(PT.measure(with_images)['images'], 2)
        self.assertGreater(PT.measure(with_images)['image_text'], 0)

    def test_the_owners_law_firm_page_is_inside_the_business_table(self):
        self.assertEqual(PT.judge('business', self.doc), [])

    def test_each_type_has_its_own_table_the_same_page_fails_the_others(self):
        findings = {name: PT.judge(name, self.doc) for name in PT.TYPES}
        self.assertTrue(any('images=0' in f for f in findings['portfolio']))       # a portfolio needs pictures
        self.assertTrue(any('sections=8' in f for f in findings['landing']))        # a landing page is short
        self.assertGreater(len({tuple(v) for v in findings.values()}), 3)

    def test_a_value_just_outside_a_range_is_found_and_just_inside_is_not(self):
        hi = PT.thresholds('business')['images'][1]
        pad = lambda n: self.doc.replace('</main>', '<img src="a" alt="a">' * n + '</main>')
        self.assertFalse(any(f.startswith('images=') for f in PT.judge('business', pad(hi))))
        self.assertTrue(any(f.startswith('images=') for f in PT.judge('business', pad(hi + 1))))

    def test_an_unknown_type_raises_in_the_judge_too(self):
        with self.assertRaises(PT.UnknownPageType):
            PT.judge('hologram', self.doc)


if __name__ == '__main__':
    unittest.main()
