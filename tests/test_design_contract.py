"""Warehouse 125: the design contract of each category (the owner 2026-11-21; "4א", 2026-11-27: every palette gains a
declared dark variant and a declared light variant).

The contract is data the model picks from, not something it makes up: vertical_palettes.json holds each palette's colours
and its two variants, section_library/directions.json holds the direction's font scale, the spacing rhythm, the font cap
and the contrast rules. Every check here runs on the real data and the real code: the G-APPLE contract builds each
variant (and corrects nothing), the section library renders a page in each and the static gate judges it, library.css is
read for the sizes the direction declares, and colour_roles takes the declared variant a customer's "dark" or "light"
names, not a mix."""
import copy
import json
import os
import re
import unittest
from unittest import mock

from omni_prod import section_library as L
from omni_prod import vertical_palettes as VP
from omni_prod.g_apple import contract as C
from omni_prod.g_apple import static
from omni_prod.reference_catalog import CATEGORIES
from omni_prod.section_library import demo_law_firm as D
from omni_prod.site_content import colour_roles as CR

PALETTES = sorted(VP.load()['palettes'])
RULES = L.DIRECTIONS['contract']['contrast']


def pairs(p: dict) -> dict:
    """The four pairs the contract's rules name, measured on a {primary, accent, background, ink} palette."""
    on_primary = max(C.contrast('#ffffff', p['primary']), C.contrast('#000000', p['primary']))
    return {'ink_on_background': C.contrast(p['ink'], p['background']),
            'primary_on_background': C.contrast(p['primary'], p['background']),
            'accent_on_background': C.contrast(p['accent'], p['background']),
            'text_on_primary': on_primary}


def build(p: dict, direction: dict) -> dict:
    return C.build(f"\n--- Approved project brief\nDesign: style clean; primary colour {p['primary']}; palette {p['primary']}, "
                   f"{p['accent']}, {p['background']}, {p['ink']} (primary, accent, background, text: test); font 'Heebo', "
                   f"system-ui, sans-serif (load it from Google Fonts); display font {direction['display']}")


class EveryPaletteDeclaresTwoVariants(unittest.TestCase):
    def test_the_ten_palettes_each_declare_a_dark_and_a_light_variant(self):
        self.assertEqual(len(PALETTES), 10)
        for name in PALETTES:
            with self.subTest(palette=name):
                self.assertEqual(set(VP.variants_for(name)), {'dark', 'light'})
                for variant in VP.variants_for(name).values():
                    self.assertEqual(set(variant), set(VP.ROLES))

    def test_the_palette_and_both_variants_meet_the_contrast_rules(self):
        """WCAG AA for text and controls on every palette and variant; the declared rules are the floor."""
        self.assertGreaterEqual(min(RULES.values()), VP.AA_TEXT)
        for name in PALETTES:
            contract = L.design_contract(name)
            for variant, colours in contract['variants'].items():
                for rule, ratio in pairs(colours).items():
                    with self.subTest(palette=name, variant=variant, rule=rule):
                        self.assertGreaterEqual(ratio, contract['contrast_rules'][rule], colours)

    def test_a_variant_is_a_real_dark_or_light_page(self):
        for name in PALETTES:
            v = VP.variants_for(name)
            with self.subTest(palette=name):
                self.assertLess(C.luminance(v['dark']['background']), 0.02)
                self.assertGreater(C.luminance(v['dark']['ink']), 0.8)
                self.assertGreater(C.luminance(v['light']['background']), 0.9)
                self.assertLess(C.luminance(v['light']['ink']), 0.05)

    def test_the_contract_builds_every_variant_and_corrects_none_of_it(self):
        for name in PALETTES:
            direction = L.direction_for(name)
            for variant, colours in L.design_contract(name)['variants'].items():
                with self.subTest(palette=name, variant=variant):
                    tokens = build(colours, direction)['tokens']
                    self.assertEqual((tokens['--color-bg'], tokens['--color-text'], tokens['--color-primary']),
                                     (colours['background'], colours['ink'], colours['primary']))

    def test_a_page_in_every_variant_passes_the_static_gate(self):
        for name in PALETTES:
            direction = L.direction_for(name)
            for variant, colours in L.design_contract(name)['variants'].items():
                with self.subTest(palette=name, variant=variant):
                    contract = build(colours, direction)
                    doc, _ = L.page(dict(copy.deepcopy(D.CONTENT), direction=direction['direction']), contract)
                    self.assertEqual(static.check(doc, contract), [])

    def test_loading_refuses_a_missing_variant_and_a_variant_below_aa(self):
        data = json.loads(VP.DATA.read_text(encoding='utf-8'))
        broken = copy.deepcopy(data)
        del broken['palettes']['hearth']['dark']
        with self.assertRaisesRegex(VP.PaletteError, "palette 'hearth': no declared dark variant"):
            VP.check(broken, CATEGORIES)
        broken = copy.deepcopy(data)
        broken['palettes']['clinic']['light']['primary'] = '#99e6df'      # a pale teal on a near-white page
        with self.assertRaisesRegex(VP.PaletteError, r"clinic\.light: primary on background"):
            VP.check(broken, CATEGORIES)
        broken = copy.deepcopy(data)
        broken['palettes']['trade']['dark']['ink'] = '#555555'
        with self.assertRaisesRegex(VP.PaletteError, r"trade\.dark: ink on background"):
            VP.check(broken, CATEGORIES)
        with self.assertRaisesRegex(VP.PaletteError, 'not a palette'):
            VP.variants_for('ocean')


class TheContractFieldsAreDeclaredAndTrue(unittest.TestCase):
    def test_every_category_resolves_to_a_complete_contract(self):
        self.assertEqual(len(CATEGORIES), 32)
        for slug in CATEGORIES:
            name, _ = VP.palette_for(slug)
            contract = L.design_contract(name)
            with self.subTest(category=slug):
                self.assertEqual(set(contract), {'palette', 'direction', 'display', 'font_scale', 'spacing_rhythm',
                                                 'font_cap', 'contrast_rules', 'variants'})
                self.assertEqual(contract['direction'], L.direction_for(name)['direction'])
                self.assertEqual(set(contract['variants']), {'base', 'dark', 'light'})

    def test_the_sizes_are_tokens_of_the_g_apple_contract(self):
        for direction in L.DIRECTIONS['directions']:
            scale = L.DIRECTIONS['contract']['directions'][direction]['font_scale']
            with self.subTest(direction=direction):
                self.assertEqual(set(scale), {'hero', 'title', 'body', 'small'})
                self.assertLessEqual(set(scale.values()), set(C.TYPE_PX))
        rhythm = L.DIRECTIONS['contract']['spacing_rhythm']
        self.assertLessEqual(set(rhythm.values()), set(C.SPACE_PX))
        self.assertEqual(set(L.DIRECTIONS['contract']['directions']), set(L.DIRECTIONS['directions']))

    def test_the_declared_scale_and_rhythm_are_what_library_css_sets(self):
        css = (L.HERE / 'library.css').read_text(encoding='utf-8')
        for direction in L.DIRECTIONS['directions']:
            scale = L.DIRECTIONS['contract']['directions'][direction]['font_scale']
            with self.subTest(direction=direction):
                own = re.search(r'\[data-direction="%s"\] \.hero h1 \{ font-size: var\(--text-(\d+)\)' % direction, css)
                hero = int(own.group(1)) if own else int(re.search(r'\n\.hero h1 \{ font-size: var\(--text-(\d+)\)', css).group(1))
                own = re.search(r'\[data-direction="%s"\] \.title(?:, [^{]*)? \{ font-size: var\(--text-(\d+)\)' % direction, css)
                title = int(own.group(1)) if own else int(re.search(r'\n\.title \{ font-size: var\(--text-(\d+)\)', css).group(1))
                body = int(re.search(r'\nbody \{[^}]*font-size: var\(--text-(\d+)\)', css).group(1))
                self.assertEqual((hero, title, body), (scale['hero'], scale['title'], scale['body']))
        rhythm = L.DIRECTIONS['contract']['spacing_rhythm']
        self.assertIn('.section { padding-block: var(--space-%d); }' % rhythm['section'], css)
        self.assertIn('.section-head { margin-block-end: var(--space-%d); }' % rhythm['section_head'], css)

    def test_the_font_cap_is_the_contracts_two_weights_and_every_page_loads_at_most_two_families(self):
        cap = L.DIRECTIONS['contract']['font_cap']
        self.assertEqual(cap['weights'], list(C.WEIGHTS))
        for name in PALETTES:
            direction = L.direction_for(name)
            contract = build(L.design_contract(name)['variants']['base'], direction)
            links = L.font_links(contract)
            families = re.findall(r'family=([^&:]+)', links)
            with self.subTest(palette=name):
                self.assertLessEqual(len(set(families)), cap['families'], links)
                self.assertEqual(set(re.findall(r'wght@([\d;]+)', links)) - {'400;700'}, set())


class ColourRolesTakeTheDeclaredVariants(unittest.TestCase):
    CLAUSE = "requested colour description '%s'"

    def test_dark_and_light_are_the_declared_variant_not_a_mix_of_the_primary(self):
        for name in PALETTES:
            palette = {r: VP.load()['palettes'][name][r] for r in VP.ROLES}
            variants = VP.variants_for(name)
            for word, said in (('dark', 'כהה'), ('light', 'בהיר')):
                with self.subTest(palette=name, word=word):
                    got = CR.roles(self.CLAUSE % said, palette, variants)
                    self.assertEqual({r: got[r] for r in VP.ROLES}, variants[word])
                    self.assertNotEqual(got['background'], C._mix(palette['primary'], '#000000', 0.9))

    def test_a_stated_colour_still_wins_over_the_variants_primary(self):
        name = 'blush'
        palette = {r: VP.load()['palettes'][name][r] for r in VP.ROLES}
        got = CR.roles("#1e40af requested colour description 'dark'", palette, VP.variants_for(name))
        self.assertEqual((got['primary'], got['background']), ('#1e40af', VP.variants_for(name)['dark']['background']))

    def test_a_description_word_with_no_variants_raises(self):
        palette = {r: VP.load()['palettes']['blush'][r] for r in VP.ROLES}
        for variants in (None, {}, {'dark': VP.variants_for('blush')['dark']}):
            with self.subTest(variants=variants), self.assertRaisesRegex(ValueError, 'no declared light variant'):
                CR.roles(self.CLAUSE % 'light', palette, variants)

    def test_the_content_route_passes_the_category_palettes_variants(self):
        """site_content.decide on a real brief with 'dark' takes the declared dark variant of the category's palette."""
        from omni_prod import site_content as SC
        from tests.test_colour_roles import OWNER, prompt_with
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
            route = SC.decide(prompt_with('כהה'), OWNER)
        self.assertEqual(route.route, 'section_library', route.reason)
        name = route.palette
        self.assertEqual(route.contract_source, 'category+dark')
        self.assertEqual(route.contract['tokens']['--color-bg'], VP.variants_for(name)['dark']['background'])


if __name__ == '__main__':
    unittest.main()
