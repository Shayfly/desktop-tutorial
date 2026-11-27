"""Warehouse item 69 (released by the owner 2026-11-15): the output type is routed first (A0).

A request whose family has no output profile is refused out loud on the first turn, in the customer's words, with no
default chosen, no question asked, no brief saved and no model called. A family with a profile proceeds exactly as
before. A family the registry does not know raises. The real path is ConversationSupervisor.turn -- the production
code with the deterministic interpreter; the in-memory brief and conversation stores stand in for SQL only.

Evidence that this was broken: on main 86eb9bb, "אני רוצה משחק פלטפורמות קטן לטלפון" was answered with
"בחרתי עבורכם ... שאלה אחת לפני שממשיכים" and the question personal_data, while feasibility already said UNSUPPORTED
(scratchpad/probe_unsupported.py, 2026-11-15).
"""
from __future__ import annotations

import importlib.util
import unittest
from unittest import mock

from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs

GAME = 'אני רוצה משחק פלטפורמות קטן לטלפון, עם שלבים וניקוד'
SONG = 'אני רוצה שיר לחתונה של אחותי, משהו שמח בעברית'
IOS = 'אפליקציה לאייפון למעקב הוצאות'
SITE = 'אתר לעסק שלי, אטליז הגבעה, עם שעות פתיחה וטלפון'
# words a 60-year-old customer should never have to read in a refusal (plan, part B section 13)
JARGON = ('דפדפן', 'api', 'מנוע', 'פרופיל', 'runtime', 'engine', 'profile', 'backend', 'שרת', 'unsupported')


def supervisor():
    return ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())


class RegistryTruth(unittest.TestCase):
    def test_profiles_are_exactly_the_executable_families(self):
        from omni_prod.intake.families import EXECUTABLE
        from omni_prod.output_profile import PROFILES
        self.assertEqual(set(PROFILES), set(EXECUTABLE))

    def test_every_family_is_declared_exactly_once(self):
        from omni_prod.intake.families import FAMILIES
        from omni_prod.output_profile import PROFILES, UNSUPPORTED
        self.assertEqual(set(PROFILES) | set(UNSUPPORTED), set(FAMILIES))
        self.assertFalse(set(PROFILES) & set(UNSUPPORTED))

    def test_the_truth_check_stops_a_profile_the_engine_cannot_build(self):
        from omni_prod.intake.families import EXECUTABLE, FAMILIES
        from omni_prod.output_profile import PROFILES, UNSUPPORTED, check_truth
        # a profile for a family the engine cannot build, moved out of the unsupported set: only the first check sees
        # it (NC2 of 2026-11-15 caught the earlier version of this case, which the other two checks also stopped)
        with self.assertRaises(RuntimeError):
            check_truth({**PROFILES, 'media': PROFILES['website']}, {k: v for k, v in UNSUPPORTED.items() if k != 'media'},
                        EXECUTABLE, FAMILIES)
        with self.assertRaises(RuntimeError):          # an executable family without a profile
            check_truth({k: v for k, v in PROFILES.items() if k != 'website'}, UNSUPPORTED, EXECUTABLE, FAMILIES)
        with self.assertRaises(RuntimeError):          # a family declared nowhere
            check_truth(PROFILES, {k: v for k, v in UNSUPPORTED.items() if k != 'media'}, EXECUTABLE, FAMILIES)

    def test_a_profile_declares_what_the_engine_enforces(self):
        from omni_prod import pricing
        from omni_prod.output_profile import PROFILES
        from omni_prod.planning.feasibility import CORE_CHECKS
        for kind, p in PROFILES.items():
            with self.subTest(kind):
                self.assertEqual(set(p.gates), set(CORE_CHECKS))
                self.assertEqual(p.cost_ceiling_usd, pricing.m5_class_llm_cap(pricing.CostClass.LIGHT))
                self.assertEqual(p.repair_rounds_max, pricing.DEFAULT_REPAIR_ROUNDS)
                for module in p.acceptance_checks:
                    self.assertIsNotNone(importlib.util.find_spec(module), module)
                self.assertTrue(p.required_brief_fields)
                self.assertFalse(set(p.required_brief_fields) & set(p.forbidden_brief_fields))
                self.assertEqual(p.to_dict()['cost_ceiling_usd'], str(p.cost_ceiling_usd))

    def test_an_unknown_family_raises_instead_of_a_quiet_default(self):
        from omni_prod.output_profile import ProfileMissing, route
        for bad in ('hologram', '', 'GAME'):
            with self.subTest(bad), self.assertRaises(ProfileMissing):
                route(bad)

    def test_every_refusal_says_not_yet_and_what_is_possible_without_jargon(self):
        from omni_prod.output_profile import UNSUPPORTED, route
        for fam in UNSUPPORTED:
            with self.subTest(fam):
                he, en = route(fam).not_yet('he'), route(fam).not_yet('en')
                self.assertIn('עוד לא', he)
                self.assertIn('כן:', he)
                self.assertIn('not yet', en)
                self.assertIn('Yes:', en)
                for word in JARGON:
                    self.assertNotIn(word, he.lower(), (fam, word))
                    self.assertNotIn(word, en.lower(), (fam, word))
        with self.assertRaises(ValueError):
            route('website').not_yet('he')


class Router(unittest.TestCase):
    def refuse(self, text, fam, lang='he'):
        from omni_prod.output_profile import route
        sup = supervisor()
        t = sup.turn(project_id='p', account_id='a', message=text, lang=lang)
        self.assertEqual(t.reply, route(fam).not_yet(lang))
        self.assertEqual(t.unsupported, fam)
        self.assertEqual(t.questions, [])
        self.assertIsNone(t.brief_row)                                   # no brief: no default was chosen
        self.assertEqual([a['type'] for a in t.actions], ['describe_web_instead'])
        self.assertNotIn('בחרתי עבורכם', t.reply)
        self.assertEqual(t.to_dict(lang)['unsupported'], fam)
        stored = [m for m in sup.store.messages_for('p', limit=10) if m['role'] == 'assistant'][-1]
        self.assertEqual(stored['interpretation'].get('unsupported'), fam)     # counted, not only said
        self.assertEqual(stored['content'], t.reply)
        return sup

    def test_a_game_request_is_refused_before_any_question(self):
        self.refuse(GAME, 'game')

    def test_a_song_and_a_native_app_are_refused_too(self):
        self.refuse(SONG, 'media')
        self.refuse(IOS, 'mobile_app')
        self.refuse('I want a platformer game for my phone', 'game', 'en')

    def test_no_interpreter_and_no_model_run_for_a_refused_type(self):
        with mock.patch.object(ConversationSupervisor, '_classify', side_effect=AssertionError('A0 runs first')), \
                mock.patch.object(ConversationSupervisor, '_interpreter', side_effect=AssertionError('no model')):
            self.refuse(GAME, 'game')

    def test_the_exit_is_the_keyboard(self):
        sup = self.refuse(GAME, 'game')
        t = sup.turn(project_id='p', account_id='a', message=SITE)
        self.assertIsNone(t.unsupported)
        self.assertIsNotNone(t.brief_row)
        self.assertNotIn('עוד לא', t.reply)

    def test_a_website_request_is_untouched(self):
        t = supervisor().turn(project_id='p', account_id='a', message=SITE)
        self.assertIsNone(t.unsupported)
        self.assertIsNotNone(t.brief_row)
        self.assertEqual(t.actions, [])
        self.assertNotIn('עוד לא', t.reply)

    def test_a_website_for_a_game_shop_is_a_website(self):
        from omni_prod.intake.families import classify_family
        for text in ('אתר לחנות משחקים', 'דף נחיתה לחוג משחקי חשיבה', 'אתר לאולפן מוזיקה',
                     'אתר עם סרטון תדמית בעמוד הבית', 'שלום, אתר לעסק שלי'):
            with self.subTest(text):
                self.assertEqual(classify_family(text), 'website')
                t = supervisor().turn(project_id='p', account_id='a', message=text)
                self.assertIsNone(t.unsupported)
                self.assertIsNotNone(t.brief_row)
        self.assertEqual(classify_family('משחק דפדפן באתר לחברת משחקים'), 'game')    # the opening product wins

    def test_a_photo_caption_is_not_a_media_request(self):
        from omni_prod.intake.families import requested_family
        self.assertIsNone(requested_family('תמונה של החנות'))
        self.assertIsNone(requested_family('המטרה: למכור משחקים לילדים'))
        self.assertEqual(requested_family('תבנה לי משחק פלטפורמות'), 'game')
        self.assertEqual(requested_family('אתר לחנות משחקים'), 'website')

    def test_a_passing_mention_never_refuses_or_restarts_a_brief(self):
        sup = supervisor()
        first = sup.turn(project_id='p', account_id='a', message=SITE)
        t = sup.turn(project_id='p', account_id='a', message='המטרה: למכור משחקים לילדים')
        self.assertIsNone(t.unsupported)
        self.assertIsNotNone(t.brief_row)
        self.assertEqual(sup.briefs.latest('p').brief.prompt, first.brief_row.brief.prompt)

    def test_an_explicit_request_for_another_product_is_refused_without_touching_the_brief(self):
        from omni_prod.output_profile import route
        sup = supervisor()
        first = sup.turn(project_id='p', account_id='a', message=SITE)
        t = sup.turn(project_id='p', account_id='a', message='תבנה לי משחק פלטפורמות')
        self.assertEqual(t.unsupported, 'game')
        self.assertEqual(t.reply, route('game').not_yet('he'))
        self.assertEqual(t.brief_row.revision, first.brief_row.revision)
        self.assertEqual(sup.briefs.latest('p').fingerprint, first.brief_row.fingerprint)

    def test_the_question_playbooks_have_no_silent_default(self):
        from omni_prod.intake.question_skills import checklist
        for fam in ('hologram', None, ''):
            with self.subTest(fam), self.assertRaises(LookupError):
                checklist(fam)


if __name__ == '__main__':
    unittest.main()
