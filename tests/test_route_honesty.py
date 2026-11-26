"""Route honesty: the owner's build bld_3938e570 (2026-11-25) failed in production -- cause 1, the wrong business.

The brief is the production row, read read-only and redacted (tests/fixtures/site_content_bld_3938e570.json: its
database hash, the redaction, and the production evidence the fixes are measured against). A smoke shop (hookahs,
tobacco, rolling papers, lighters) that asked for a picture next to each category, a page per category and to upload
more products later. Production: site_route 'all preconditions hold', category 'lawyers' found 'nearest', domain
'lawyer'; the copy model, told it wrote for a law firm, left out the lawyer palette's process and FAQ, was made to
write them, and the build died on one sentence: sections.process.lead PRICE_NOT_GIVEN (53 s of work, $0.053, refunded).

  1. (here) the business is only a category the brief NAMES (vertical_palettes.identify): no signal is no category --
     no domain, no domain facts, no trade words, no palette name for the model, and the neutral palette's own process
     and FAQ are offered, not required; a near word or a trigram match lends the palette only

The real decide(), validator, section library and payload; nothing is scripted here (AGENTS.md rule 2)."""
import hashlib
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from tests.test_site_content_engine import PROMPT as LAW

from omni_prod import site_content as SC
from omni_prod import vertical_palettes as VP
from omni_prod.site_content import agents as A
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import schema as K

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_3938e570.json').read_text(encoding='utf-8'))
GOA = FIXTURE['prompt']
PROD = FIXTURE['production_site_route']
OWNER = {'user_id': 'usr_owner_test'}


def on():
    return mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'})


def decide(prompt, **kw):
    with on():
        return SC.decide(prompt, OWNER, year='2026', **kw)


def with_request(text: str, prompt: str = LAW) -> str:
    """The prompt with `text` added to the customer's request (before the approved brief)."""
    end = prompt.index('--- Approved project brief')
    return prompt[:end] + text + '\n' + prompt[end:]


def payload(route, prompt):
    sheet = Fx.fact_sheet(prompt)
    offered, _ = K.offered_sections(sheet, route.palette_entry, route.order, route.outline_titles)
    return A.ContentSiteGenerator.__new__(A.ContentSiteGenerator)._payload(route, sheet, offered)


class TheFixture(unittest.TestCase):
    def test_it_is_the_production_row_redacted(self):
        self.assertEqual(hashlib.sha256(GOA.encode('utf-8')).hexdigest(), FIXTURE['prompt_sha256'])
        self.assertEqual(FIXTURE['production_prompt_sha256'],
                         'cb5cb3b81ec48e9f454412524b2635f5360acfcd3a5a85f9784f0acf8e3e7433')
        for placeholder, n in (('ישראל ישראלי', 2), ('+972 50-555-1234', 4), ('רחוב הרצל 10 ירושלים', 4)):
            self.assertEqual(GOA.count(placeholder), n, placeholder)
        # production's evidence: the smoke shop was decided as a law firm
        self.assertEqual((PROD['category'], PROD['category_found'], PROD['domain'], PROD['reason']),
                         ('lawyers', 'nearest', 'lawyer', 'all preconditions hold'))
        self.assertEqual(VP.nearest_category(Fx.request_text(GOA)), (VP.NO_SIGNAL, 0.0))     # no signal at all


class TheBusinessIsOnlyWhatTheBriefNames(unittest.TestCase):
    def test_no_signal_is_no_category(self):
        route = decide(GOA)
        said = route.to_dict()
        self.assertEqual((route.route, route.reason), ('section_library', 'all preconditions hold'))
        self.assertEqual((said['category'], said['category_found'], said['domain'], said['domain_facts']),
                         (None, 'none', None, []))
        self.assertEqual(route.domain_words, [])
        self.assertEqual(said['palette_category'], VP.NO_SIGNAL)
        # the colours, the art direction, the fonts and the design contract are production's: only the identity went
        self.assertEqual((said['palette'], said['direction'], said['font_pair'], said['contract']),
                         (PROD['palette'], PROD['direction'], PROD['font_pair'], PROD['contract']))

    def test_the_neutral_palettes_process_and_faq_are_offered_not_required(self):
        route = decide(GOA)
        offered, _ = K.offered_sections(Fx.fact_sheet(GOA), route.palette_entry, route.order, route.outline_titles)
        self.assertEqual({k for k, need in offered.items() if need == 'required'}, set(SC.UNNAMED_REQUIRED))
        self.assertEqual((offered['process'], offered['faq']), ('optional', 'optional'))
        # the law firm names its category: the counsel palette's sections stay required there
        law = decide(LAW.replace('מבנה הדף:', 'מה חשוב לי:'))
        offered, _ = K.offered_sections(Fx.fact_sheet(law.prompt), law.palette_entry, law.order, law.outline_titles)
        self.assertEqual((law.category, law.category_found, offered['process'], offered['faq']),
                         ('lawyers', 'named', 'required', 'required'))

    def test_the_model_is_never_told_a_trade_the_brief_did_not_name(self):
        route = decide(GOA)
        said = payload(route, GOA)
        self.assertEqual((said['palette'], said['trade_words']), (None, []))
        self.assertIn('process (optional section: include it only with real content)', said['schema']['sections'])
        self.assertIn('faq (optional section: include it only with real content)', said['schema']['sections'])
        law = payload(decide(LAW), LAW)
        self.assertEqual(law['palette'], 'counsel')
        self.assertTrue(law['trade_words'])

    def test_a_near_word_or_an_inflection_lends_the_palette_only(self):
        cases = {'אתר לסטודיו קעקועים': ('photographers', 'nearest'),        # declared near (colour), not the trade
                 'אתר לסוכן ביטוח': ('accountants', 'nearest'),
                 'אתר לחשמלאית': ('electrical', 'nearest'),                   # a trigram inflection
                 'אתר לחנות עישון': (VP.NO_SIGNAL, 'none'),
                 'אתר לצלמת': ('photographers', 'named')}
        for text, (palette_category, found) in cases.items():
            with self.subTest(text):
                who = VP.identify(text)
                self.assertEqual((who['palette_category'], who['found']), (palette_category, found))
                self.assertEqual(who['category'], palette_category if found == 'named' else None)
        tattoo = GOA.replace('לעסק למוצרי עישון', 'לסטודיו קעקועים', 1)
        route = decide(tattoo)
        self.assertEqual((route.category, route.category_found, route.palette_category, route.domain),
                         (None, 'nearest', 'photographers', None))


if __name__ == '__main__':
    unittest.main()
