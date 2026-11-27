"""S6.3 slice 0: one direction function for the build and the direction sketch (site_content.direction).

decide() used to hold the category, palette, art direction, font pair, design contract and section order inline; the
sketch would have needed a copy of it, and a copy drifts (the sketch would show a direction the build does not take).
Now decide() calls direction(). Two things are proved on the real functions:

* decide() answers exactly what it answered before the extraction: `tests/fixtures/site_direction_golden.json` holds
  `decide().to_dict()` of every case below, captured on origin/main (bc7077e, with #551's colour_roles) BEFORE the change, with its sha256;
* direction() agrees with the Route decide() returns, field by field, and names the same reason when it fails."""
import hashlib
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import site_content as SC
from omni_prod.section_library import DIRECTIONS

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))
PROMPT = FIXTURE['prompt']
GOLDEN_FILE = ROOT / 'tests' / 'fixtures' / 'site_direction_golden.json'
OWNER = {'user_id': 'usr_owner_test'}


_LAW_FIRM = 'משרד עורכי דין "כהן ושות׳ – דיני עבודה"'


def _with_request(text: str, prompt: str = PROMPT) -> str:
    end = prompt.index('--- Approved project brief')
    return prompt[:end] + text + '\n' + prompt[end:]


def cases() -> dict[str, str]:
    """The prompts the golden file was captured from: the owner's law-firm brief and one change per route decision."""
    return {
        'owner_brief': PROMPT,
        'outline_unmapped': PROMPT.replace('4. איך זה עובד:', '4. הצוות שלנו:', 1),
        'outline_repeated': PROMPT.replace('4. איך זה עובד:', '4. שירותים:', 1),
        'outline_hero_not_first': PROMPT.replace('1. פתיח:', '1. תחומי עיסוק:', 1).replace('2. תחומי התמחות:', '2. פתיח:', 1),
        'outline_without_basis': PROMPT.replace('4. איך זה עובד:', '4. המלצות:', 1),
        'name_not_declared': PROMPT.replace('"כהן ושות׳ – דיני עבודה"', 'כהן ושות׳ – דיני עבודה'),
        # a brief with no Design line locks nothing to complete (a described colour no longer lands here: colour_roles, #551)
        'no_design_contract': PROMPT.replace(
            "Design: style formal; primary colour #1e3a5f; palette #1e3a5f, #ffffff; requested colour description "
            "'כחול כהה, לבן'; font 'Heebo', system-ui, sans-serif (load it from Google Fonts with a system "
            "fallback); define these as CSS custom properties.\n", ''),
        'phone_not_one': _with_request('טלפון נוסף: 04-8123456.'),
        'icon_image': _with_request('אני רוצה גם לוגו למשרד.'),
        'several_pictures': _with_request('אני רוצה 3 תמונות של המשרד.'),
        'not_content_only': PROMPT.replace('Product kind: CONTENT-ONLY website', 'Product kind: web app'),
        # other trades through the same brief: another palette, another art direction, another font pair
        'salon': PROMPT.replace(_LAW_FIRM, 'מספרה "סטודיו נועה"'),
        'restaurant': PROMPT.replace(_LAW_FIRM, 'פיצריה "פיצה רומא"').replace('3 עורכי דין', '3 ספרים').replace(
            'דיני עבודה', 'תספורות'),
        'unnamed_subject': _with_request('אני רוצה אתר לחנות הקטנה שלי.'),
    }


def decide_all() -> dict[str, dict]:
    with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
        return {k: SC.decide(p, OWNER, year='2026').to_dict() for k, p in cases().items()}


def canonical(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, sort_keys=True)


class DecideIsUnchangedByTheExtraction(unittest.TestCase):
    def test_decide_answers_what_it_answered_on_main(self):
        golden = json.loads(GOLDEN_FILE.read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(canonical(golden['routes']).encode('utf-8')).hexdigest(), golden['sha256'],
                         'the golden file was edited by hand')
        got = decide_all()
        self.assertEqual(set(got), set(golden['routes']))
        for case, route in got.items():
            with self.subTest(case=case):
                self.assertEqual(canonical(route), canonical(golden['routes'][case]))

    def test_the_golden_cases_cover_both_the_route_and_its_legacy_reasons(self):
        reasons = {r['reason'].split(':')[0] for r in decide_all().values()}
        self.assertIn('all preconditions hold', reasons)
        self.assertTrue({'outline_unmapped', 'name_not_declared', 'no_design_contract',
                         'outline_without_basis'} <= reasons, reasons)


class DirectionAgreesWithTheRoute(unittest.TestCase):
    def test_every_field_the_route_carries_comes_from_direction(self):
        for case, prompt in cases().items():
            with self.subTest(case=case):
                with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
                    route = SC.decide(prompt, OWNER, year='2026')
                d = SC.direction(prompt, lang='he')
                if route.route == SC.ROUTE:
                    self.assertIsNone(d.reason)
                    self.assertEqual((route.palette, route.direction, route.voice),
                                     (d.palette, d.entry['direction'], d.entry['voice']))
                    self.assertEqual((route.contract_fp, route.contract_source),
                                     (d.contract['fingerprint'], d.contract_source))
                    self.assertEqual((route.script, route.font_pair, route.order, route.outline_titles),
                                     (d.script, d.pair['id'], d.order, d.titles))
                    self.assertEqual((route.category, route.category_found, route.palette_category, route.domain),
                                     tuple(d.domain_kw[k] for k in ('category', 'category_found',
                                                                    'palette_category', 'domain')))
                elif d.reason:
                    self.assertEqual(route.reason, d.reason)
                else:
                    # a legacy reason decided before the direction (the route's own preconditions)
                    self.assertIn(route.reason.split(':')[0], {'not_content_only', 'icon_image', 'several_pictures',
                                                                'phone_not_one', 'not_hebrew'}, route.reason)

    def test_the_owners_brief_direction(self):
        d = SC.direction(PROMPT, lang='he')
        self.assertEqual((d.reason, d.palette, d.entry['direction'], d.pair['id']),
                         (None, 'counsel', 'formal', 'he-frank-heebo'))
        self.assertEqual(d.order, ['hero', 'services', 'about', 'process', 'faq', 'contact'])

    def test_a_failed_step_names_itself_and_stops_there(self):
        d = SC.direction(cases()['outline_unmapped'], lang='he')
        self.assertTrue(d.reason.startswith('outline_unmapped'), d.reason)
        self.assertIsNone(d.order)
        with mock.patch.dict(DIRECTIONS['palettes'], {}, clear=True):
            gone = SC.direction(PROMPT, lang='he')
        self.assertTrue(gone.reason.startswith('palette_not_in_library'), gone.reason)
        self.assertIsNone(gone.contract)

    def test_the_build_never_asks_for_the_sketchs_phone_allowance(self):
        seen = []
        real = SC.direction

        def spy(*a, **kw):
            seen.append(kw.get('phone_optional', False))
            return real(*a, **kw)
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}), mock.patch.object(SC, 'direction', spy):
            SC.decide(PROMPT, OWNER, year='2026')
        self.assertEqual(seen, [False])

    def test_two_phones_stay_a_problem_even_when_the_phone_is_optional(self):
        two = _with_request('טלפון נוסף: 04-8123456.')
        self.assertEqual(SC.direction(two, lang='he').reason, 'phone_not_one')
        self.assertEqual(SC.direction(two, lang='he', phone_optional=True).reason, 'phone_not_one')

    def test_direction_reads_no_flag(self):
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'bogus'}):
            self.assertIsNone(SC.direction(PROMPT, lang='he').reason)


if __name__ == '__main__':
    unittest.main()
