"""The second colour reaches the page (the owner, 2026-11-22: for a business we do not know, ask which colours the
customer likes and which take more or less space).

Before, the design contract kept one colour of the palette's two (`dropped: 'one accent colour: the primary'`), so the
colour a customer named for the smaller part was recorded in the brief and never rendered. Contract version 2 locks it
as --color-accent (a mark seen on the page, 3:1), --color-on-accent (text inside it, 4.5:1) and --color-accent-text
(small text in it, 4.5:1 on the page, the surface and the 5% primary tint). The section library uses it for small marks
only; the primary stays the one action colour."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from omni_prod import vertical_palettes as V
from omni_prod.g_apple import contract as C

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'omni_prod' / 'section_library' / 'library.css').read_text(encoding='utf-8')


def brief(primary, accent, bg, ink, style='clean'):
    return (f"\n--- Approved project brief\nDesign: style {style}; primary colour {primary}; palette {primary}, {accent}, "
            f"{bg}, {ink} (primary, accent, background, text); font 'Heebo', system-ui, sans-serif (load it from Google "
            f"Fonts with a system fallback)")


def rules_using(token: str) -> list[str]:
    """The selectors of every library.css rule whose declarations use var(<token>)."""
    body = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)
    return [sel.strip() for sel, decl in re.findall(r'([^{}]+)\{([^{}]*)\}', body) if f'var({token})' in decl]


class TheCustomersSecondColourIsKept(unittest.TestCase):
    def test_navy_and_gold_keeps_the_gold(self):
        # the owner's tutor brief: "בעיקר כחול כהה וקצת זהב" -- mostly dark blue, a little gold
        c = C.build(brief('#1e3a8a', '#d4a017', '#ffffff', '#111827'))
        t = c['tokens']
        self.assertEqual(t['--color-primary'], '#1e3a8a')
        accent = C._rgb(t['--color-accent'])
        self.assertTrue(accent[0] > accent[2] and accent[1] > accent[2], f'the accent is still gold: {t["--color-accent"]}')
        self.assertNotIn('dropped', c)
        self.assertIn('--color-accent:', c['css'])

    def test_the_fingerprint_binds_the_accent(self):
        gold = C.build(brief('#1e3a8a', '#d4a017', '#ffffff', '#111827'))
        green = C.build(brief('#1e3a8a', '#15803d', '#ffffff', '#111827'))
        self.assertNotEqual(gold['fingerprint'], green['fingerprint'])
        self.assertEqual(gold, C.build(brief('#1e3a8a', '#d4a017', '#ffffff', '#111827')))       # deterministic


class EveryPaletteStaysReadable(unittest.TestCase):
    def test_every_catalogue_palette_and_hard_cases(self):
        palettes = [(p['primary'], p['accent'], p['background'], p['ink']) for p in V.load()['palettes'].values()]
        palettes += [('#1e3a8a', '#ffff00', '#ffffff', '#111827'),     # a yellow accent on white: 1.1:1 as given
                     ('#f59e0b', '#fde68a', '#111827', '#f9fafb'),     # a dark page with a pale accent
                     ('#111827', '#111827', '#ffffff', '#111827')]     # the accent equal to the primary and the ink
        self.assertGreaterEqual(len(palettes), 10)
        for p in palettes:
            with self.subTest(palette=p):
                c = C.build(brief(*p))
                m = c['contrast']
                self.assertGreaterEqual(m['accent on bg'], C.MIN_UI_CONTRAST)
                self.assertGreaterEqual(m['on-accent on accent'], C.MIN_TEXT_CONTRAST)
                for ground in ('bg', 'surface', 'tint'):
                    self.assertGreaterEqual(m[f'accent-text on {ground}'], C.MIN_TEXT_CONTRAST)


class TheLibraryUsesItForSmallMarksOnly(unittest.TestCase):
    def test_the_marks_use_the_accent(self):
        text = ' | '.join(rules_using('--color-accent-text'))
        for sel in ('.eyebrow', '.stat dd', '.faq summary::after'):
            self.assertIn(sel, text)
        marks = ' | '.join(rules_using('--color-accent'))
        self.assertIn('.steps li::before', marks)
        self.assertIn('.quote', marks)

    def test_no_button_section_or_link_is_in_the_accent(self):
        used = rules_using('--color-accent') + rules_using('--color-accent-text') + rules_using('--color-on-accent')
        for sel in used:
            for banned in ('.btn', 'section--primary', 'section--tint', '.site-header', 'a ', 'a{', ':focus'):
                self.assertNotIn(banned, sel + '{', f'the accent is for small marks, not {sel}')
        self.assertNotRegex(CSS, r'background:\s*var\(--color-accent(-text)?\)[^;]*;[^}]*\}\s*/\*\s*section')
        self.assertLessEqual(len(set(used)), 6, f'the accent spread beyond small marks: {used}')

    def test_the_generator_is_told_the_same(self):
        rules = C.rules(C.build(brief('#1e3a8a', '#d4a017', '#ffffff', '#111827')))
        self.assertIn('--color-accent, is for small marks only', rules)
        self.assertIn('Never a section background or a button in the accent', rules)


if __name__ == '__main__':
    unittest.main()
