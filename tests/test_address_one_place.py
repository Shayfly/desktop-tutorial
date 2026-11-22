"""One address spelled twice is one place (2026-11-22, the owner's brief for "סטודיו נועה", bld_1d477f37).

The conversation's summary wrote the address as "רחוב הרצל 12 בחולון" while the customer wrote "רחוב הרצל 12, חולון". The
fact canon held two addresses, so the content route (site_content.facts) said address_not_one and sent the build to the
old path, and the old path's page said "גם בכתובת" -- a second branch that does not exist. The fixture is the owner's
own brief, read from production (tests/fixtures/owner_brief_noa/README.md).
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import discovery as d
from omni_prod import fact_canon as F
from omni_prod.site_content import facts as Fx

FIX = Path(__file__).resolve().parent / 'fixtures' / 'owner_brief_noa' / 'brief.json'


def approved_prompt() -> str:
    """The build prompt as the approval flow makes it (investor_app: brief.prompt + requirements_text)."""
    brief = d.Brief.from_dict(json.loads(FIX.read_text(encoding='utf-8')))
    return brief.prompt + '\n' + d.requirements_text(brief)


def addresses(text: str) -> list[str]:
    return [f.source_ref for f in F.build_canon(text).facts if f.key == 'address']


class TheOwnersBrief(unittest.TestCase):
    def test_the_brief_holds_both_spellings(self):
        prompt = approved_prompt()
        self.assertIn('רחוב הרצל 12, חולון', prompt)
        self.assertIn('רחוב הרצל 12 בחולון', prompt)            # the summary's spelling, in "Initial content"

    def test_one_place_and_the_customers_spelling_stands(self):
        self.assertEqual(addresses(approved_prompt()), ['רחוב הרצל 12, חולון'])

    def test_the_route_no_longer_says_address_not_one(self):
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
            problems = Fx.fact_sheet(approved_prompt()).problems
        self.assertNotIn('address_not_one', problems)
        self.assertEqual(problems, ['phone_not_one'])           # the WhatsApp answer kept no role: a separate fix


class SpellingsOfOnePlace(unittest.TestCase):
    def test_the_city_with_in_or_without_it(self):
        for customer, summary in (('רחוב הרצל 12, חולון', 'רחוב הרצל 12 בחולון'),
                                  ('רחוב יגאל אלון 94, תל אביב', 'רחוב יגאל אלון 94 בתל אביב'),
                                  ('רחוב ז׳בוטינסקי 45, רמת גן', 'רחוב ז׳בוטינסקי 45 ברמת גן'),
                                  ('רחוב הרצל 30, רחובות', 'רחוב הרצל 30 ברחובות'),
                                  ('רחוב הרצל 12, בני ברק', 'רחוב הרצל 12 בבני ברק'),
                                  ('רחוב הרצל 12, חולון', 'רחוב הרצל 12')):
            with self.subTest(summary):
                self.assertTrue(F.same_place(customer, summary))
                text = f'המשרד ב{customer}. טלפון 03-6091234.\nInitial content: {summary}'
                self.assertEqual(addresses(text), [customer])

    def test_another_place_stays_another_place(self):
        for a, b in (('רחוב הרצל 12, חולון', 'רחוב הרצל 14, חולון'), ('רחוב הרצל 12, חולון', 'רחוב הרצל 12, בת ים'),
                     ('רחוב הרצל 12, חולון', 'רחוב ויצמן 12, חולון'), ('רחוב הרצל 12', 'רחוב הרצל 120'),
                     ('רחוב הרצל 12, חולון', 'רחוב הרצל 12 בבת ים')):
            with self.subTest(b):
                self.assertFalse(F.same_place(a, b))
        self.assertEqual(len(addresses('סניף א: רחוב הרצל 12, חולון. סניף ב: רחוב ויצמן 3, חולון.')), 2)
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
            self.assertIn('address_not_one', Fx.fact_sheet(
                'אתר תדמית. טלפון 03-5551234. סניף א: רחוב הרצל 12, חולון. סניף ב: רחוב ויצמן 3, חולון.').problems)


class TheThreeBriefsTheOwnerWasGiven(unittest.TestCase):
    """The three projects recommended to the owner on 2026-11-22: each one phone, one place, even when the summary
    spells the address with ב."""

    BRIEFS = {
        'lawyer': ('אתר תדמית למשרד עורכי הדין "לוי את שחר". המשרד ברחוב יגאל אלון 94, תל אביב. טלפון 03-6091234.',
                   'רחוב יגאל אלון 94 בתל אביב'),
        'restaurant': ('אתר תדמית למסעדה "זית ולימון". רחוב ז׳בוטינסקי 45, רמת גן, הכניסה מהחצר. טלפון 03-6721234.',
                       'רחוב ז׳בוטינסקי 45 ברמת גן'),
        'tutor': ('אתר תדמית למורה פרטית למתמטיקה. שיעורים ברחוב הרצל 30, רחובות, או בזום. טלפון 054-7712345.',
                  'רחוב הרצל 30 ברחובות'),
    }

    def test_no_route_problem_with_the_summarys_spelling(self):
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
            for name, (brief, summary) in self.BRIEFS.items():
                with self.subTest(name):
                    self.assertEqual(Fx.fact_sheet(f'{brief}\nInitial content: {summary}').problems, [])


if __name__ == '__main__':
    unittest.main()
