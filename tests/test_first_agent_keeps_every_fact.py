"""The first agent keeps every fact the customer gives (the owner, 2026-11-23: "סוכן ... שידע להבין את הלקוח ... ולהפוך את
המלל לתוצאה מעולה", and on ShayFly: the packages and prices were lost).

Production replay (tests/fixtures/shayfly_lost_facts.json, read-only rows of prj_5wRH_CceL2aSeQ): the model understood
each turn and proposed the new facts for `content` and `screens`. agent.apply called each one "differs from a
confirmed requirement", kept the old text, and the customer read "קודם נקבע ... לא שיניתי — מה נכון?". By the summary
(rev 8) the site had no packages, no prices, no "מי אנחנו", no name and no phone.

Here the same recorded proposals run through the real apply: new facts are ADDED to what is there, nothing is asked
back, and the model's own reply is what the customer reads.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from omni_prod import discovery as d
from omni_prod.intake import agent as A
from omni_prod.intake.interpreter import Interpretation, Proposal

FX = json.loads((Path(__file__).parent / 'fixtures' / 'shayfly_lost_facts.json').read_text(encoding='utf-8'))


def brief0():
    return d.Brief.from_dict({'prompt': 'בנה אתר מכירה של ShayFly בעברית', 'fields': json.loads(json.dumps(FX['brief_rev2_fields']))})


def interp(turn):
    return Interpretation(language='he', product_family='website', interpreter='model',
                          proposals=[Proposal(**p) for p in turn['proposals']], reply=turn['model_reply'])


def replay():
    b, results = brief0(), []
    for turn in FX['turns']:
        r = A.apply(b, interp(turn))
        results.append(r)
        b = r.brief
    return b, results


class EveryFactStays(unittest.TestCase):
    def test_the_packages_and_prices_reach_the_brief(self):
        b, _ = replay()
        content = b.values()['content']
        for fact in ('פראג', 'אומן', 'פאפוס', '2300', '2500', '1990', 'פנסיון מלא'):
            self.assertIn(fact, content, fact)

    def test_what_was_there_before_stays_too(self):
        b, _ = replay()
        self.assertIn('בדקו איתנו', b.values()['content'])
        self.assertIn('חיוג בלחיצה', b.values()['screens'])

    def test_about_us_the_name_and_the_phone_reach_the_brief(self):
        b, _ = replay()
        self.assertIn('מי אנחנו', b.values()['screens'])
        self.assertIn('שי נסים אוחנה', b.values()['content'])
        self.assertIn('0503456723', b.values()['content'])

    def test_nothing_is_asked_back(self):
        _, results = replay()
        self.assertEqual([c['field'] for r in results for c in r.conflicts], [])

    def test_a_fact_said_twice_is_kept_once(self):
        b, _ = replay()
        again = Interpretation(language='he', product_family='website', interpreter='model',
                               proposals=[Proposal(**FX['turns'][0]['proposals'][1])])
        content = A.apply(b, again).brief.values()['content']
        self.assertEqual(content.count('2300'), 1)


class SafetyStillAsks(unittest.TestCase):
    def test_a_privacy_choice_is_still_confirmed_not_overwritten(self):
        b = brief0()
        flip = Interpretation(language='he', product_family='website', interpreter='model',
                              proposals=[Proposal('personal_data', 'yes', 'high', 'נשמור שמות', 'model')])
        r = A.apply(b, flip)
        self.assertEqual(r.brief.values()['personal_data'], 'no')
        self.assertEqual([c['field'] for c in r.conflicts], ['personal_data'])


if __name__ == '__main__':
    unittest.main()


class TwoItemsAreNeverOne(unittest.TestCase):
    def test_two_packages_that_differ_only_by_price_stay_two(self):
        b = d.answer(d.start('אתר חבילות נופש'), {'content': 'חבילה 1: 3 לילות 2000 ₪'})
        more = Interpretation(language='he', product_family='website', interpreter='model', proposals=[
            Proposal('content', 'חבילה 2: 3 לילות 2500 ₪', 'high', 'x', 'model')])        # package 2 alone, as said
        content = A.apply(b, more).brief.values()['content']
        self.assertIn('2000', content)
        self.assertIn('2500', content)
