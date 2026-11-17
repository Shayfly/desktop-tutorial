"""Phase 2 of the conversation agent (the owner, 2026-11-17): the model asks the customer-only decision itself, in its
own words, with why it matters -- the context it gets says which decision, what it means and the choices; nothing in
it says "buttons". And the expert checklist is the one of the PRODUCT, not of the last message."""
import json
import os
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.intake import conversation_agent as A
from omni_prod.intake import interpreter as I

REQUEST = 'אתר תדמית לחברת דלתות, טלפון 050-345-6723'


def context(message, brief, flag):
    with mock.patch.dict(os.environ, {A.FLAG: flag}):
        user = I.contextual_user(message, brief, [])
    return json.loads(user[user.index('{'):user.index('\nCurrent customer message:')])


def held_brief():
    b = d.start(REQUEST)
    b.detector, b.open_material = True, ['personal_data']
    return b


class TheModelAsksIt(unittest.TestCase):
    def test_with_the_agent_the_open_decision_is_given_to_the_model_to_ask(self):
        ctx = context('כן', held_brief(), '1')
        self.assertEqual(ctx['asked_with_buttons'], [])
        nxt = ctx['ask_next']
        self.assertEqual(nxt['topic'], 'personal_data')                     # the detector's own order
        self.assertEqual(nxt['meaning'], d.BY_ID['personal_data'].he)
        self.assertEqual(nxt['choices'], [o.he for o in d.BY_ID['personal_data'].options])
        self.assertTrue(nxt['why_it_matters'])
        self.assertEqual(list(ctx)[0], 'ask_next')                           # first: the context is cut at 2400

    def test_the_rules_tell_it_to_ask_in_its_own_words_and_never_answer_for_them(self):
        self.assertIn('context.ask_next', I.SYSTEM)
        self.assertIn('in your own words', I.SYSTEM)
        self.assertIn('Never answer it for them', I.SYSTEM)

    def test_without_the_agent_the_buttons_are_as_before(self):
        ctx = context('כן', held_brief(), '0')
        self.assertNotIn('ask_next', ctx)
        self.assertIn('personal_data', ctx['asked_with_buttons'])

    def test_the_checklist_is_the_products_not_the_last_messages(self):
        from omni_prod.intake.question_skills import checklist
        ctx = context('כן', held_brief(), '1')
        self.assertEqual(ctx['expert_checklist'], checklist('website'))


if __name__ == '__main__':
    unittest.main()
