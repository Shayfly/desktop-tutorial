"""The D10 adversarial review's remaining findings (wf_8c2f9499-486), each on the real supervisor (owner 2026-11-18:
"an overrun stops the conversation and does not crash it").

- the pre-check closed a conversation for good on a quote that was only held by a call in flight;
- the closed state lived only in the last assistant message, so any reply without a limit reopened the paid path;
- the follow-up wording ignored the kind: after 'daily' the conversation "had ended", after 'busy' a real stop never
  said why; two 'busy' replies in a row became "I did not see a change";
- 'busy' on the turn that completed the spec dropped the summary; an 'Updated:' line made at the limit was dropped;
- a late paid reply after a daily pause was closed as 'daily'; an image-only message read "the provider is busy";
- Venice's preferred model fell back to the next one silently.
The counting fixes (an EXECUTING call is in flight; unknown tokens are None) run on real PostgreSQL in
tests/test_conversation_turn_cap_pg.py.
"""
import os
import sys
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import _TXT, ConversationSupervisor, _AtLimit
from omni_prod.intake.interpreter import Interpretation
from omni_prod.intake.worker_route import ReservedWorkerInterpreter
from omni_prod.providers import venice as V

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_limit import LimitFrom          # noqa: E402
from test_conversation_os import MemoryBriefs          # noqa: E402
from test_uploaded_main_image import PHOTO             # noqa: E402

HE = _TXT['he']
DOORS = R.SCENARIOS['doors']['lines'][0]
WORKER = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.15',
          'OMNI_INTAKE_DAILY_BUDGET_USD': '1.00'}


class AgentOn(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1', 'OMNI_INTAKE_MODEL': '1'})
        p.start()
        self.addCleanup(p.stop)


class ThePreCheckLeavesInFlightToReserve(unittest.TestCase):
    """$0.105 settled and $0.045 held by a call in flight: the pre-check used to read $0.15 spent and close the
    conversation for good. A hold is not spend; reserve() tells 'busy' from 'budget' under the scope locks."""

    def interpreter(self, held):
        class Svc:
            def counted(self, scope):
                return Decimal('0.15') if scope.startswith('project:') else Decimal('0')

            def open_held(self, scope):
                return held
        with mock.patch.dict(os.environ, WORKER):
            sup = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), reservations=Svc(),
                                         enqueue=lambda rid: None)
            return sup._interpreter('p', 'acct')

    def test_a_held_quote_goes_to_reserve(self):
        self.assertIsInstance(self.interpreter(Decimal('0.045')), ReservedWorkerInterpreter)

    def test_settled_spend_still_closes_at_the_precheck(self):
        it = self.interpreter(Decimal('0'))
        self.assertIsInstance(it, _AtLimit)
        self.assertEqual(it.kind, 'budget')


class TheClosedStateHolds(AgentOn):
    def test_a_reply_without_a_limit_in_between_does_not_reopen_the_paid_path(self):
        lf = LimitFrom(start=2)
        sup = R._Supervisor(lf)
        sup.turn(project_id='c', account_id='a', message=DOORS, lang='he')
        stop = sup.turn(project_id='c', account_id='a', message='יש לנו גם תצוגה בחנות', lang='he')
        self.assertTrue(stop.reply.startswith(HE['limit_budget']), stop.reply)
        # a button answer, an intent reply or an image turn stores no limit
        sup.store.add_message(project_id='c', account_id='a', role='assistant', content='כאן הסיכום שביקשתם.',
                              interpretation={'intent': 'missing'})
        calls = lf.calls
        t = sup.turn(project_id='c', account_id='a', message='עוד פרט', lang='he')
        self.assertEqual(lf.calls, calls)                           # no model was asked
        self.assertEqual(t.interpretation['limit']['kind'], 'budget')
        self.assertEqual(sup._closed('c'), 'budget')


class TheWordingFollowsTheKind(AgentOn):
    def test_a_stop_after_busy_says_why_it_stopped(self):
        sup = R._Supervisor(LimitFrom(start=1, kind='busy'))
        first = sup.turn(project_id='b', account_id='a', message=DOORS, lang='he')
        sup._interpreter = lambda *a, **k: LimitFrom(start=1, kind='budget')
        second = sup.turn(project_id='b', account_id='a', message='יש לנו גם תצוגה בחנות', lang='he')
        self.assertTrue(first.reply.startswith(HE['limit_busy']), first.reply)
        self.assertTrue(second.reply.startswith(HE['limit_budget']), second.reply)

    def test_two_busy_replies_alternate_and_never_say_no_change(self):
        sup = R._Supervisor(LimitFrom(start=1, kind='busy'))
        first = sup.turn(project_id='bb', account_id='a', message=DOORS, lang='he')
        second = sup.turn(project_id='bb', account_id='a', message=DOORS, lang='he')
        self.assertTrue(first.reply.startswith(HE['limit_busy']), first.reply)
        self.assertTrue(second.reply.startswith(HE['limit_busy_alt']), second.reply)
        self.assertNotIn(HE['rephrase'], second.reply)

    def test_two_daily_pauses_say_later_never_ended(self):
        sup = R._Supervisor(LimitFrom(start=1, kind='daily'))
        first = sup.turn(project_id='d', account_id='a', message=DOORS, lang='he')
        second = sup.turn(project_id='d', account_id='a', message='יש לנו גם תצוגה בחנות', lang='he')
        self.assertTrue(first.reply.startswith(HE['limit_daily']), first.reply)
        self.assertTrue(second.reply.startswith(HE['limit_daily_alt']), second.reply)
        self.assertNotIn(HE['limit_still'], second.reply)


class WhatTheClosingKeeps(AgentOn):
    def closing(self, kind, parts, actions=()):
        sup = R._Supervisor(LimitFrom(start=10 ** 6))
        t = sup.turn(project_id='k', account_id='a', message=DOORS, lang='he')
        t.actions = list(actions)
        return sup._closing_turn('k', t, t.brief_row, {'kind': kind, 'source': 'reserve'}, parts, 'he', HE)

    def test_busy_on_the_turn_that_completed_the_spec_keeps_the_summary(self):
        t = self.closing('busy', ['סיכום המפרט: אתר לחנות דלתות.'], [{'type': 'approve_spec', 'brief_revision': 1}])
        self.assertIn('סיכום המפרט', t.reply)
        self.assertIn('approve_spec', [a['type'] for a in t.actions])

    def test_an_update_made_at_the_limit_is_told(self):
        t = self.closing('budget', [HE['corrected'] + ': התחברות למשתמשים עם סיסמה'])
        self.assertIn(HE['corrected'] + ': התחברות', t.reply)


class LateAndImageTurns(AgentOn):
    def test_a_late_paid_reply_after_a_daily_pause_is_not_closed_as_daily(self):
        sup = R._Supervisor(LimitFrom(start=1, kind='daily'))
        sup.turn(project_id='l', account_id='a', message=DOORS, lang='he')
        late = Interpretation('he', 'website')
        late.interpreter, late.reservation_id = 'deterministic', 'irs_late'
        self.assertIsNone(sup._turn_limit('l', late, {}))

    def test_an_image_only_message_is_never_provider_busy(self):
        sup = R._Supervisor(LimitFrom(start=2))
        sup.turn(project_id='i', account_id='a', message=DOORS, lang='he')
        sup.turn(project_id='i', account_id='a', message='יש לנו גם תצוגה בחנות', lang='he')
        t = sup.turn(project_id='i', account_id='a', attachments=[PHOTO], lang='he')
        self.assertNotIn(HE['model_unavailable'], t.reply)


class TheFallbackIsNeverSilent(unittest.TestCase):
    def model(self, mid, cin, cout):
        return V.VeniceModel(id=mid, input_usd_per_m=Decimal(cin), output_usd_per_m=Decimal(cout),
                             privacy='anonymized', e2ee=False, tools=False)

    def test_haiku_answering_for_sonnet_is_logged_with_the_reason(self):
        with self.assertLogs('omni_prod.providers.venice', 'WARNING') as logs:
            m = V.select_model([self.model('claude-haiku-5-5', '0.1', '0.5')],
                               allowed=('claude-sonnet-5-5', 'claude-haiku-5-5'), prefer_order=True)
        self.assertEqual(m.id, 'claude-haiku-5-5')
        self.assertIn('VENICE_PREFERRED_MODEL_UNAVAILABLE preferred=claude-sonnet-5-5 chosen=claude-haiku-5-5',
                      logs.output[0])

    def test_the_preferred_model_answers_without_a_warning(self):
        with self.assertNoLogs('omni_prod.providers.venice', 'WARNING'):
            m = V.select_model([self.model('claude-haiku-5-5', '0.1', '0.5'), self.model('claude-sonnet-5-5', '2', '10')],
                               allowed=('claude-sonnet-5-5', 'claude-haiku-5-5'), prefer_order=True)
        self.assertEqual(m.id, 'claude-sonnet-5-5')


if __name__ == '__main__':
    unittest.main()
