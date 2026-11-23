"""A restated text that keeps the confirmed text and adds to it is an extension, not a conflict (production
2026-11-19, the owner's law-firm site: the WhatsApp number was asked about as "קודם נקבע ... מה נכון?" turn after
turn). The values below are the two sides of that question, as the reply showed them."""
import unittest

from omni_prod import discovery as d
from omni_prod.intake import agent
from omni_prod.intake.interpreter import Interpretation, Proposal

OLD = 'כתובת: דרך מנחם בגין 132, תל אביב; טלפון 03-5551234; office@cohen-law.co.il; א׳–ה׳ 09:00–18:00; ייעוץ ראשון 250 ₪'
NEW = OLD + '; וואטסאפ 050-5551234'


def brief_with_content(value):
    return d.answer(d.start('אתר תדמית למשרד עורכי דין'), {'content': value})


def proposal(value, confidence='high'):
    return Interpretation('he', 'web_app', [Proposal('content', value, confidence, 'x', 'model')])


class AnExtensionIsApplied(unittest.TestCase):
    def test_the_whatsapp_line_extends_the_content(self):
        res = agent.apply(brief_with_content(OLD), proposal(NEW))
        self.assertEqual(res.conflicts, [])
        self.assertEqual(res.brief.fields['content']['value'], NEW)
        self.assertEqual(res.brief.fields['content']['source'], 'message')

    def test_the_same_text_with_other_separators_and_one_more_fact_extends_it(self):
        res = agent.apply(brief_with_content(OLD), proposal(OLD.replace('; ', ' | ') + ' | וואטסאפ 050-5551234'))
        self.assertEqual(res.conflicts, [])


class AChangeIsAppliedAndNothingIsLost(unittest.TestCase):
    """The owner, 2026-11-23: the first agent never asks "what is right?" about the site's content. A fact said again
    with another number is the customer's correction; a restatement that leaves a fact out never loses it."""

    def test_a_changed_fact_replaces_its_own_clause_and_is_said_back(self):
        res = agent.apply(brief_with_content(OLD), proposal(OLD.replace('250', '300')))
        self.assertEqual(res.conflicts, [])
        self.assertEqual(res.brief.fields['content']['value'], OLD.replace('250', '300'))
        self.assertEqual(res.corrected, [{'field': 'content', 'old': 'ייעוץ ראשון 250 ₪', 'new': 'ייעוץ ראשון 300 ₪'}])

    def test_a_dropped_fact_is_kept(self):
        res = agent.apply(brief_with_content(OLD), proposal(OLD.split('; ייעוץ')[0]))
        self.assertEqual(res.conflicts, [])
        self.assertEqual(res.brief.fields['content']['value'], OLD)

    def test_a_medium_guess_never_extends_a_confirmed_text(self):
        res = agent.apply(brief_with_content(OLD), proposal(NEW, 'medium'))
        self.assertEqual(res.brief.fields['content']['value'], OLD)


if __name__ == '__main__':
    unittest.main()
