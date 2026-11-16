"""Warehouse 105 (owner 2026-11-16; was 80): the colour mapping is a data file, and #1d4ed8 is gone.

Acceptance: a vertical without a palette fails; all 32 verticals are mapped.

Real path: omni_prod/vertical_palettes.json as committed, loaded by vertical_palettes.load() against
reference_catalog.CATEGORIES, and discovery.start -> requirements_text, the build prompt's Design line."""
from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path

from omni_prod import discovery as d
from omni_prod import vertical_palettes as V
from omni_prod.reference_catalog import CATEGORIES

ROOT = Path(__file__).resolve().parents[1]


def contrast(a: str, b: str) -> float:
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def design(prompt: str) -> str:
    [line] = [x for x in d.requirements_text(d.start(prompt)).splitlines() if x.startswith('Design:')]
    return line


class TheDataFile(unittest.TestCase):
    def test_all_32_verticals_are_mapped_to_a_palette(self):
        data = V.load()
        self.assertEqual(len(CATEGORIES), 32)
        self.assertEqual(set(data['categories']), set(CATEGORIES))
        self.assertEqual(len(data['palettes']), 10)
        for slug in CATEGORIES:
            with self.subTest(slug):
                name, p = V.palette_for(slug)
                self.assertIn(name, data['palettes'])
                self.assertEqual(set(p), set(V.ROLES))

    def test_a_vertical_without_a_palette_fails(self):
        data = json.loads(V.DATA.read_text(encoding='utf-8'))
        broken = copy.deepcopy(data)
        del broken['categories']['butcher']
        with self.assertRaisesRegex(V.PaletteError, r"categories without a palette: \['butcher'\]"):
            V.check(broken, CATEGORIES)
        broken = copy.deepcopy(data)
        broken['categories']['butcher']['palette'] = 'ocean'
        with self.assertRaisesRegex(V.PaletteError, "no palette named 'ocean'"):
            V.check(broken, CATEGORIES)
        broken = copy.deepcopy(data)
        broken['categories']['florists'] = {'palette': 'hearth', 'words': ['פרחים']}
        with self.assertRaisesRegex(V.PaletteError, 'not in the catalogue'):
            V.check(broken, CATEGORIES)
        broken = copy.deepcopy(data)
        broken['palettes']['hearth']['primary'] = 'blue'
        with self.assertRaisesRegex(V.PaletteError, 'must be #rrggbb'):
            V.check(broken, CATEGORIES)

    def test_every_palette_is_readable(self):
        for name, p in V.load()['palettes'].items():
            with self.subTest(name):
                self.assertGreaterEqual(contrast(p['primary'], '#ffffff'), 4.5)    # white text on a button
                self.assertGreaterEqual(contrast(p['ink'], p['background']), 4.5)

    def test_every_vertical_is_recognised_by_its_own_words(self):
        for slug, entry in V.load()['categories'].items():
            with self.subTest(slug):
                self.assertEqual(V.category_of(f'אתר ל{entry["words"][0]} בחיפה'), slug)


class TheOldBlueIsGone(unittest.TestCase):
    def test_1d4ed8_is_nowhere_in_the_product(self):
        found = [str(p.relative_to(ROOT)) for p in (ROOT / 'omni_prod').rglob('*')
                 if p.suffix in ('.py', '.js', '.css', '.json', '.html') and '1d4ed8' in p.read_text(errors='ignore').lower()]
        self.assertEqual(found, [])

    def test_the_colour_question_recommends_the_category_not_blue(self):
        q = d.BY_ID['color']
        self.assertEqual(q.recommended, 'category')
        self.assertEqual(q.options[0].value, 'category')


class TheBuildPrompt(unittest.TestCase):
    def test_a_butcher_without_a_colour_gets_the_butcher_palette(self):
        line = design('אתר לאטליז של שמעון, טלפון 0504000162')
        _, p = V.palette_for('butcher')
        self.assertIn(f'primary colour {p["primary"]}', line)
        self.assertIn('the customer stated no colour', line)

    def test_two_verticals_get_two_palettes(self):
        self.assertNotEqual(V.palette_for('butcher')[1]['primary'], V.palette_for('dental')[1]['primary'])
        self.assertIn(V.palette_for('dental')[1]['primary'], design('אתר למרפאת שיניים בחולון'))

    def test_the_customers_colour_wins(self):
        line = design('אתר לאטליז, בצבע ירוק')
        self.assertIn('primary colour #15803d', line)
        self.assertNotIn(V.palette_for('butcher')[1]['primary'], line)

    def test_an_unknown_business_is_said_not_defaulted(self):
        line = design('דף לחנות פרחים קטנה')
        self.assertIn('the business category is not recognised', line)
        self.assertIsNone(re.search(r'primary colour #', line))


if __name__ == '__main__':
    unittest.main()
