"""A game goes through the product route, behind a flag (the owner, 2026-11-27, answer 11; warehouse 134, plan S12.1).

Until now the A0 router refused every game ("משחק עוד לא"). Now `game` has an output profile (builder `canvas_game_v1`) and the
refusal is a question of ROLLOUT: OMNI_OUTPUT_GAME = off (default) | owner | all, asked per account
(feature_flags.output_rollout). The real path is ConversationSupervisor.turn (the deterministic interpreter, in-memory stores
standing in for SQL only), the real route(), and the real intake contract compiled from the brief the conversation made.

What this does NOT show: the game's own questions (what you do, how you win). The conversation still asks the web app's
fields for a game (see STATUS.md); acceptance 6 of warehouse 134 is open.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from omni_prod.feature_flags import output_rollout
from omni_prod.pricing import _FOUNDER_DEFAULT
from tests.test_output_profile_router import GAME, JARGON, SITE, supervisor

OTHER = 'usr_not_the_owner'


def flag(value=None):
    env = {k: v for k, v in os.environ.items() if k != 'OMNI_OUTPUT_GAME'}
    if value is not None:
        env['OMNI_OUTPUT_GAME'] = value
    return mock.patch.dict(os.environ, env, clear=True)


class TheRollout(unittest.TestCase):
    def test_a_game_is_off_by_default_for_everyone_the_owner_included(self):
        with flag():
            self.assertFalse(output_rollout('game', _FOUNDER_DEFAULT))
            self.assertFalse(output_rollout('game', OTHER))
            self.assertFalse(output_rollout('game'))

    def test_owner_lets_only_the_owners_account_through_and_all_lets_everyone(self):
        with flag('owner'):
            self.assertTrue(output_rollout('game', _FOUNDER_DEFAULT))
            self.assertFalse(output_rollout('game', OTHER))
            self.assertFalse(output_rollout('game', None))
            self.assertFalse(output_rollout('game', ''))
        with flag('all'):
            self.assertTrue(output_rollout('game', OTHER))
        with flag('OFF'):
            self.assertFalse(output_rollout('game', _FOUNDER_DEFAULT))

    def test_any_other_value_raises_it_is_never_read_as_off_or_all(self):
        for bad in ('on', 'yes', '1', 'owners', 'true'):
            with self.subTest(bad), flag(bad), self.assertRaises(ValueError):
                output_rollout('game', _FOUNDER_DEFAULT)

    def test_a_type_with_no_rollout_defined_raises_and_sites_and_apps_are_always_through(self):
        with flag(), self.assertRaises(ValueError):
            output_rollout('hologram', OTHER)
        with flag():
            self.assertTrue(output_rollout('website', OTHER))
            self.assertTrue(output_rollout('web_app', OTHER))
        with mock.patch.dict(os.environ, {'OMNI_OUTPUT_WEBSITE': 'owner'}):
            self.assertFalse(output_rollout('website', OTHER))        # a variable is honoured when someone sets it


class TheProfile(unittest.TestCase):
    def test_game_is_executable_and_has_its_own_profile_and_the_truth_check_still_holds(self):
        from omni_prod.intake.families import EXECUTABLE, FAMILIES
        from omni_prod.output_profile import (BUILDER_CANVAS_GAME_V1, PROFILES, ROLLOUT_REFUSALS, UNSUPPORTED, check_truth)
        self.assertIn('game', EXECUTABLE)
        p = PROFILES['game']
        self.assertEqual(p.builder, BUILDER_CANVAS_GAME_V1)
        self.assertEqual(p.builder, 'canvas_game_v1')
        self.assertEqual(p.acceptance_checks, ('omni_prod.game_kit.probe',))
        self.assertEqual(p.asset_kinds, ('art',))
        self.assertNotIn('game', UNSUPPORTED)
        self.assertIn('game', ROLLOUT_REFUSALS)
        check_truth(PROFILES, UNSUPPORTED, EXECUTABLE, FAMILIES)

    def test_a_site_and_an_app_keep_the_web_builder_and_the_games_brief_carries_none_of_a_sites_fields(self):
        from omni_prod.output_profile import BUILDER_WEB_V1, PROFILES
        self.assertEqual({PROFILES['website'].builder, PROFILES['web_app'].builder}, {BUILDER_WEB_V1})
        game = PROFILES['game']
        for site_only in ('content_only', 'login', 'personal_data', 'dates', 'duplicates'):
            self.assertIn(site_only, game.forbidden_brief_fields, site_only)
            self.assertNotIn(site_only, game.required_brief_fields, site_only)
        self.assertEqual(set(game.required_brief_fields), {'audience', 'languages', 'style', 'color'})
        self.assertFalse(set(game.required_brief_fields) & set(game.forbidden_brief_fields))

    def test_the_probe_module_the_profile_names_exists(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('omni_prod.game_kit.probe'))


class TheRouter(unittest.TestCase):
    def test_with_the_flag_off_the_refusal_is_the_one_every_customer_got_before_and_no_model_was_asked(self):
        from omni_prod.output_profile import ROLLOUT_REFUSALS, route
        for account in (_FOUNDER_DEFAULT, OTHER, None):
            with self.subTest(account), flag():
                routing = route('game', account)
                self.assertFalse(routing.supported)
                self.assertIs(routing.unsupported, ROLLOUT_REFUSALS['game'])
                self.assertEqual(routing.not_yet('he')[:9], 'משחק עוד לא'[:9])
                he, en = routing.not_yet('he'), routing.not_yet('en')
                self.assertIn('עוד לא', he)
                self.assertIn('not yet', en)
                for word in JARGON:
                    self.assertNotIn(word, he.lower())
                    self.assertNotIn(word, en.lower())

    def test_with_the_flag_on_for_the_owner_the_owner_gets_the_profile_and_another_account_the_refusal(self):
        from omni_prod.output_profile import route
        with flag('owner'):
            mine, other = route('game', _FOUNDER_DEFAULT), route('game', OTHER)
        self.assertTrue(mine.supported)
        self.assertEqual(mine.profile.builder, 'canvas_game_v1')
        self.assertFalse(other.supported)

    def test_every_other_family_routes_exactly_as_before(self):
        from omni_prod.output_profile import PROFILES, UNSUPPORTED, route
        with flag('owner'):
            for fam in ('website', 'web_app'):
                self.assertIs(route(fam, OTHER).profile, PROFILES[fam])
            for fam in UNSUPPORTED:
                self.assertFalse(route(fam, _FOUNDER_DEFAULT).supported, fam)

    def test_a_page_type_is_still_not_a_game(self):
        from omni_prod.output_profile import detect_page_type
        with flag('all'):
            self.assertEqual(detect_page_type('game', GAME).found, 'not_a_page')


class TheConversation(unittest.TestCase):
    def turn(self, account, message=GAME, lang='he'):
        sup = supervisor()
        return sup.turn(project_id='p', account_id=account, message=message, lang=lang), sup

    def test_flag_off_the_owner_and_everyone_are_refused_exactly_as_before(self):
        from omni_prod.output_profile import route
        for account in (_FOUNDER_DEFAULT, OTHER):
            with self.subTest(account), flag():
                t, sup = self.turn(account)
                self.assertEqual(t.reply, route('game').not_yet('he'))
                self.assertEqual(t.unsupported, 'game')
                self.assertIsNone(t.brief_row)
                self.assertEqual(t.questions, [])

    def test_flag_owner_another_account_is_still_refused_and_the_owner_is_not(self):
        with flag('owner'):
            other, _ = self.turn(OTHER)
            mine, _ = self.turn(_FOUNDER_DEFAULT)
        self.assertEqual(other.unsupported, 'game')
        self.assertIsNone(other.brief_row)
        self.assertIsNone(mine.unsupported)
        self.assertIsNotNone(mine.brief_row)
        self.assertNotIn('עוד לא', mine.reply)

    def test_flag_all_everyone_is_through(self):
        with flag('all'):
            t, _ = self.turn(OTHER)
        self.assertIsNone(t.unsupported)
        self.assertIsNotNone(t.brief_row)

    def test_a_site_request_is_unaffected_by_the_flag(self):
        for value in (None, 'owner', 'all'):
            with self.subTest(value), flag(value):
                t, _ = self.turn(OTHER, message=SITE)
                self.assertIsNone(t.unsupported)
                self.assertIsNotNone(t.brief_row)

    def test_the_contract_the_conversation_compiles_says_game_and_that_is_what_the_worker_reads(self):
        from omni_prod.game_kit.builder import is_game_build
        from omni_prod.intake import contract
        with flag('owner'):
            t, _ = self.turn(_FOUNDER_DEFAULT)
        c = contract.from_brief(t.brief_row.brief)
        self.assertEqual(c.product_family, 'game')
        self.assertTrue(is_game_build({'build_contract': {'product_family': c.product_family}}))
        self.assertFalse(is_game_build({'build_contract': {'product_family': 'website'}}))
        self.assertFalse(is_game_build({'build_contract': None}))
        self.assertFalse(is_game_build({}))


if __name__ == '__main__':
    unittest.main()
