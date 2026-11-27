"""S6.3 slice 3: the offer of a direction sketch inside a conversation turn (omni_prod/direction_sketch/offer.py and the
supervisor's `_offer_sketch`). No database: the brief is the real discovery brief, the readiness and the fingerprints are the
real functions, and the supervisor method is the real one. A turn only OFFERS; nothing here renders or calls a model."""
import logging
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from omni_prod import direction_sketch as DS
from omni_prod import discovery as D
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.direction_sketch import offer as O

ACCOUNT = 'usr_offer_test'
SALON = 'אני רוצה אתר תדמית למספרה שלי בחיפה, קוראים לה "סטודיו נועה". טלפון 04-5551234'
ENV = {'OMNI_DIRECTION_SKETCH': 'on', 'OMNI_SITE_LIBRARY': 'on'}


def row(text=SALON, revision=1):
    brief = D.start(text)
    return SimpleNamespace(brief=brief, revision=revision, fingerprint=brief.fingerprint())


class TheOffer(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)

    def offer(self, r=None, **kw):
        args = dict(account_id=ACCOUNT, has_version=False, has_open_build=False, messages=())
        args.update(kw)
        return O.offer(r or row(), **args)

    def test_a_ready_brief_gets_one_action_bound_to_its_direction_and_words(self):
        r = row()
        got = self.offer(r)
        action = got['action']
        d = DS.direction_of(r.brief)
        self.assertEqual(action, {'type': 'direction_sketch', 'direction_fp': DS.direction_fp(d),
                                  'copy_fp': DS.copy_fp(d), 'brief_revision': 1})
        self.assertEqual(got['record'], {'offered': 'now', 'direction_fp': DS.direction_fp(d)})

    def test_the_same_direction_is_offered_once(self):
        first = self.offer()['action']
        stored = [{'interpretation': {'actions': [first]}}]
        again = self.offer(messages=stored)
        self.assertIsNone(again['action'])
        self.assertEqual(again['record'], {'offered': 'already', 'direction_fp': first['direction_fp']})

    def test_a_new_direction_is_offered_again(self):
        first = self.offer()['action']
        blue = row(SALON)
        blue.brief.fields['color'] = {'value': 'כחול', 'source': 'answer', 'question_id': 'color', 'confidence': 'stated'}
        second = self.offer(blue, messages=[{'interpretation': {'actions': [first]}}])['action']
        self.assertIsNotNone(second)
        self.assertNotEqual(second['direction_fp'], first['direction_fp'])

    def test_a_brief_that_is_not_ready_says_why_and_reads_no_messages(self):
        def messages():
            raise AssertionError('the history is read only once a sketch is ready')
        got = self.offer(row('אני רוצה אתר למשרד רואי חשבון'), messages=messages)
        self.assertEqual((got['action'], got['record']), (None, {'not_ready': 'no_name'}))
        got = self.offer(has_version=True, messages=messages)
        self.assertEqual(got['record'], {'not_ready': 'already_built'})

    def test_an_off_switch_is_not_recorded_on_every_turn(self):
        with mock.patch.dict(os.environ, {'OMNI_DIRECTION_SKETCH': 'off'}):
            self.assertEqual(self.offer(), {'action': None, 'record': None})
        with mock.patch.dict(os.environ, {'OMNI_DIRECTION_SKETCH': 'accounts', 'OMNI_DIRECTION_SKETCH_ACCOUNTS': 'usr_other'}):
            self.assertEqual(self.offer(), {'action': None, 'record': None})

    def test_a_failure_is_logged_and_recorded_never_raised(self):
        with mock.patch.object(O, 'ready', side_effect=RuntimeError('boom')), self.assertLogs(O._LOG, 'ERROR') as logs:
            got = self.offer()
        self.assertEqual(got, {'action': None, 'record': {'not_ready': 'offer_failed: RuntimeError'}})
        self.assertIn('SKETCH_OFFER_FAILED', '\n'.join(logs.output))


class TheTurn(unittest.TestCase):
    """ConversationSupervisor._offer_sketch, the real method, on a stand-in for the parts of a turn it reads."""

    def setUp(self):
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.store = SimpleNamespace(messages_for=lambda project_id, limit=200: [])
        self.me = SimpleNamespace(store=self.store)

    def turn(self, r=None):
        return SimpleNamespace(brief_row=r or row(), actions=[], interpretation=None)

    def run_offer(self, turn, ctx=None):
        ConversationSupervisor._offer_sketch(self.me, turn, 'prj_1', ACCOUNT, ctx or {})

    def test_the_reply_carries_the_action_and_its_reason_is_stored(self):
        t = self.turn()
        self.run_offer(t)
        self.assertEqual([a['type'] for a in t.actions], ['direction_sketch'])
        self.assertEqual(t.interpretation['sketch']['offered'], 'now')

    def test_a_project_with_a_version_or_a_build_in_flight_gets_no_offer(self):
        for ctx in ({'latest_version_id': 'v_1'}, {'latest_build': {'status': 'running'}}, {'latest_build': {'status': 'QUEUED'}}):
            t = self.turn()
            self.run_offer(t, ctx)
            self.assertEqual((t.actions, t.interpretation), ([], {'sketch': {'not_ready': 'already_built'}}), ctx)

    def test_a_finished_failed_build_does_not_stop_a_sketch(self):
        t = self.turn()
        self.run_offer(t, {'latest_build': {'status': 'failed'}})
        self.assertEqual([a['type'] for a in t.actions], ['direction_sketch'])

    def test_a_turn_without_a_brief_is_left_alone(self):
        t = SimpleNamespace(brief_row=None, actions=[], interpretation=None)
        self.run_offer(t)
        self.assertEqual((t.actions, t.interpretation), ([], None))

    def test_an_exception_in_the_offer_never_reaches_the_turn(self):
        t = self.turn()
        with mock.patch.object(O, 'offer', side_effect=RuntimeError('boom')), self.assertLogs(level=logging.ERROR) as logs:
            self.run_offer(t)
        self.assertEqual((t.actions, t.interpretation), ([], None))
        self.assertIn('SKETCH_OFFER_FAILED', '\n'.join(logs.output))

    def test_an_unknown_flag_value_is_recorded_and_never_breaks_the_turn(self):
        t = self.turn()
        with mock.patch.dict(os.environ, {'OMNI_DIRECTION_SKETCH': 'yes'}):
            self.run_offer(t)
        self.assertEqual(t.actions, [])
        self.assertTrue(t.interpretation['sketch']['not_ready'].startswith('offer_failed: ValueError'))


class TheModelProfile(unittest.TestCase):
    def test_only_the_sketch_route_reads_the_conversation_agents_profile_for_the_sketch(self):
        from pathlib import Path
        import omni_prod
        root = Path(omni_prod.__file__).resolve().parent
        readers = sorted(str(f.relative_to(root)) for f in root.rglob('*.py')
                         if 'profile_for_sketch()' in f.read_text(encoding='utf-8', errors='replace'))
        self.assertEqual(readers, ['intake/conversation_agent.py', 'investor_app.py'])

    def test_it_is_the_conversation_agents_profile_and_no_other(self):
        from omni_prod.intake import conversation_agent as agent
        self.assertEqual(agent.profile_for_sketch(), agent.venice_profile())


if __name__ == '__main__':
    unittest.main()
