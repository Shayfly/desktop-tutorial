"""A colour answer that is not four hex colours still gives the content route a design contract (colour_roles).

Production, read-only (Neon 148ai-db-v2, project_briefs.brief_json->fields->color, 2026-11-27): the conversation model
records the customer's colour in their own words. Pairs ("שחור, זהב" x2, "צהוב, שחור"), and descriptions that no colour
table resolves ("משטח חול בהיר, טקסט פחם וכפתורים בטרקוטה" x5, "רקע פחם, שנהב ונגיעות פליז", "צבעים בהשראת בוב מארלי"
x8). Before the fix a description left the Design line without a primary colour: the contract failed and the build went
to the legacy path ('no_design_contract'); a pair set only the primary colour, so black and gold on a barber shop was
black on the blush palette's pink.

The Design line is written by the real discovery.requirements_text; the contract and the route are the real ones."""
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import discovery as D
from omni_prod import site_content as SC
from omni_prod import vertical_palettes as VP
from omni_prod.g_apple import contract as C
from omni_prod.site_content import colour_roles as CR
from omni_prod.site_content import render as R

ROOT = Path(__file__).resolve().parent.parent
PROMPT = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))['prompt']
OWNER = {'user_id': 'usr_owner_test'}
BLUSH_NAME, BLUSH = VP.palette_for('hair_salons')   # the barber's palette: pink on a pink page
BLUSH_VARIANTS = VP.variants_for(BLUSH_NAME)


def design_line(said: str) -> str:
    """The Design line the real brief writer produces for a customer's colour answer."""
    brief = D.Brief(prompt='אתר', fields={'color': {'value': said, 'source': 'message'}})
    return next(l for l in D.requirements_text(brief).split('\n') if l.startswith('Design:'))


def prompt_with(said: str) -> str:
    start = PROMPT.index('Design: ')
    end = PROMPT.index('\n', start)
    return PROMPT[:start] + design_line(said).replace('style clean', 'style formal') + PROMPT[end:]


def decide(said: str):
    with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
        return SC.decide(prompt_with(said), OWNER)


def barber(said: str):
    contract, source = R.render_contract(prompt_with(said), BLUSH, variants=BLUSH_VARIANTS)
    return contract['tokens'], source, contract


class ADescriptionIsNotALegacyBuild(unittest.TestCase):
    def test_every_description_word_takes_the_route(self):
        for said in ('כהה', 'dark', 'בהיר', 'light'):
            with self.subTest(said=said):
                route = decide(said)
                self.assertEqual(route.route, 'section_library', route.reason)

    def test_dark_and_light_pick_the_palettes_declared_variants(self):
        for said in ('כהה', 'dark'):
            tokens, source, _ = barber(said)
            self.assertEqual(source, 'category+dark')
            dark = BLUSH_VARIANTS['dark']
            self.assertEqual((tokens['--color-bg'], tokens['--color-text'], tokens['--color-primary']),
                             (dark['background'], dark['ink'], dark['primary']))
            self.assertLess(C.luminance(tokens['--color-bg']), 0.02, tokens)
            self.assertGreaterEqual(C.contrast(tokens['--color-text'], tokens['--color-bg']), 7.0)
        for said in ('בהיר', 'light'):
            tokens, source, _ = barber(said)
            light = BLUSH_VARIANTS['light']
            self.assertEqual((source, tokens['--color-bg'], tokens['--color-primary']),
                             ('category+light', light['background'], light['primary']))

    def test_a_description_word_without_declared_variants_raises_never_a_mix(self):
        for said in ('כהה', 'light'):
            with self.assertRaisesRegex(ValueError, 'no declared'):
                R.render_contract(prompt_with(said), BLUSH)

    def test_the_real_production_phrases_never_fall_to_the_legacy_path(self):
        said_in_production = ['חום, שמנת, ירוק', 'צבעים בהשראת בוב מארלי', 'כחול, כתום', 'כחול כהה, לבן',
                              'שחור, #12100e, #f2ede4, #c8763c', '#1a1512, #ede6da, #7a2e2a, כתום, אדום',
                              'משטח חול בהיר, טקסט פחם וכפתורים בטרקוטה', 'כחול, כתום, שמנת, לבן', 'חום, שמנת, לבן',
                              'לבן', 'קרם, ירוק', 'שחור, זהב', 'רקע פחם, שנהב ונגיעות פליז', 'צהוב, שחור', 'green']
        for said in said_in_production:
            with self.subTest(said=said):
                route = decide(said)
                self.assertEqual(route.route, 'section_library', route.reason)

    def test_words_nothing_knows_leave_the_category_palette_and_say_so(self):
        tokens, source, contract = barber('צבעים בהשראת בוב מארלי')
        self.assertEqual((source, tokens['--color-bg'], tokens['--color-primary']), ('category', '#fdf2f8', '#be185d'))

    def test_a_colour_name_that_holds_the_word_is_a_colour_not_a_mode(self):
        self.assertIsNone(CR.words_of('כחול כהה'))
        self.assertIsNone(CR.words_of('light blue'))
        self.assertEqual(CR.words_of('כחול כהה ובהיר'), 'light')   # the colour name is removed; the word left is "בהיר"
        self.assertIsNone(CR.words_of('כהה ובהיר'))                 # both words: nothing is said
        tokens, source, _ = barber('כחול כהה')
        self.assertEqual((source, tokens['--color-primary']), ('brief-primary+category', '#1e3a5f'))
        self.assertEqual(tokens['--color-bg'], BLUSH['background'])


class ANamedPairFillsBothRoles(unittest.TestCase):
    def test_black_and_gold_on_a_barber_is_a_black_page_with_a_gold_primary(self):
        tokens, source, contract = barber('שחור, זהב')
        self.assertEqual(source, 'brief-primary+category')
        self.assertEqual((tokens['--color-bg'], tokens['--color-primary']), ('#000000', '#ffd700'))
        self.assertNotIn(BLUSH['background'], json.dumps(tokens))      # no pink page
        self.assertNotIn(BLUSH['primary'], json.dumps(tokens))
        self.assertGreaterEqual(contract['contrast']['text on bg'], 7.0)

    def test_the_order_of_a_pair_does_not_swap_the_page(self):
        tokens, _, _ = barber('זהב, שחור')
        self.assertEqual((tokens['--color-bg'], tokens['--color-primary']), ('#000000', '#ffd700'))
        tokens, _, _ = barber('צהוב, שחור')
        self.assertEqual((tokens['--color-bg'], tokens['--color-primary']), ('#000000', '#facc15'))

    def test_two_colours_with_no_page_colour_are_primary_and_accent(self):
        _, _, contract = barber('כחול, כתום')
        self.assertEqual(contract['tokens']['--color-primary'], '#1e40af')
        self.assertEqual(contract['dropped']['accent'], '#c2410c')       # the second colour took the accent role
        self.assertEqual(contract['tokens']['--color-bg'], BLUSH['background'])

    def test_a_white_or_cream_colour_is_the_page(self):
        tokens, _, _ = barber('חום, שמנת, ירוק')
        self.assertEqual((tokens['--color-bg'], tokens['--color-primary']), ('#fffdd0', '#6b4226'))

    def test_one_colour_is_still_the_primary_on_the_category_page(self):
        tokens, _, _ = barber('שחור')
        self.assertEqual((tokens['--color-bg'], tokens['--color-primary']), (BLUSH['background'], '#000000'))

    def test_every_palette_and_phrase_makes_a_readable_contract(self):
        phrases = ['כהה', 'light', 'שחור, זהב', 'כחול, כתום', 'לבן, שחור', 'חום, שמנת, ירוק', 'צהוב, שחור', 'כחול כהה, לבן']
        for name in VP.load()['palettes']:
            palette = {r: VP.load()['palettes'][name][r] for r in VP.ROLES}
            for said in phrases:
                with self.subTest(palette=name, said=said):
                    contract, _ = R.render_contract(prompt_with(said), palette, variants=VP.variants_for(name))
                    self.assertFalse([k for k, v in contract['contrast'].items() if v < 3.0], contract['contrast'])


if __name__ == '__main__':
    unittest.main()
