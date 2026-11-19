"""An overrun stops the conversation and does not crash it (owner 2026-11-18, decision on Sonnet for the agent).

Before: a reached limit was a free-text `dropped` string. The customer read "the model provider is busy, send again in
a moment" (false), every question was cleared, and the summary could never be reached: a dead end. Now the limit is a
typed outcome (`Interpretation.limit`, {kind, source} only -- never caps or totals, the daily scope is every account's),
and the supervisor closes the conversation: why it stopped, what this message recorded, and the way on -- the summary
with its approval when the spec is ready, else the specification tab. A greeting after the stop (it takes the free
lane and never reaches the model) gets the same closing, not "provider busy"; two closing messages in a row never
repeat word for word (warehouse 113).

The supervisor is the real ConversationSupervisor (conversation_rehearsal._Supervisor, as the rehearsal runs it) and the
reservation path is the real ReservedWorkerInterpreter with a reservation service that refuses; no provider is called.
"""
import os
import sys
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import _TXT, ConversationSupervisor
from omni_prod.intake import budget as B
from omni_prod.investor_app import _conversation_message_status

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_os import MemoryBriefs        # noqa: E402
from test_conversation_rehearsal import Scripted     # noqa: E402
from test_intake_worker_route import FakeService, interp as worker_interp   # noqa: E402

HE = _TXT['he']


class LimitFrom(Scripted):
    """The rehearsal's scripted interpreter; from call `start` on, the paid call is refused with `kind`."""

    def __init__(self, start: int, kind: str = 'budget'):
        super().__init__()
        self.calls, self.start, self.kind = 0, start, kind

    def interpret(self, message, brief=None):
        out = super().interpret(message, brief)
        self.calls += 1
        if self.calls >= self.start:
            out.interpreter, out.limit = 'deterministic', {'kind': self.kind, 'source': 'reserve'}
        return out


def _reach_approval(sup, project, lines):
    """Drive a scenario until the summary with its approval is offered; returns the turn count."""
    msg = lines.pop(0)
    for n in range(1, R.MAX_TURNS + 1):
        t = sup.turn(project_id=project, account_id='a', message=msg, lang='he')
        if any(a['type'] == 'approve_spec' for a in t.actions):
            return n
        meta = sup.store.messages_for(project)[-1].get('interpretation') or {}
        asked = [x for x in meta.get('asked') or [] if x in R.TYPED]
        msg = R.TYPED[asked[0]] if asked else (lines.pop(0) if lines else 'תחליטו אתם על השאר')
    raise AssertionError('the scenario never reached the approval')


class TheConversationStopsGracefully(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1', 'OMNI_INTAKE_MODEL': '1'})
        p.start()
        self.addCleanup(p.stop)

    def test_an_incomplete_spec_closes_with_the_way_on_not_provider_busy(self):
        sup = R._Supervisor(LimitFrom(start=2))
        sup.turn(project_id='p', account_id='a', message=R.SCENARIOS['doors']['lines'][0], lang='he')
        t = sup.turn(project_id='p', account_id='a', message='יש לנו גם תצוגה בחנות', lang='he')
        self.assertTrue(t.reply.startswith(HE['limit_budget']), t.reply)
        self.assertNotIn(HE['model_unavailable'], t.reply)
        self.assertEqual(t.questions, [])                 # no card: one open question, in words
        self.assertEqual(len(getattr(t, 'asked_in_words', [])), 1)
        self.assertIn(HE['limit_ask'], t.reply)
        self.assertIn('edit_requirements', [a['type'] for a in t.actions])
        self.assertNotIn('approve_spec', [a['type'] for a in t.actions])
        self.assertEqual(t.interpretation['limit'], {'kind': 'budget', 'source': 'reserve'})

    def test_a_ready_spec_closes_with_the_summary_and_its_approval(self):
        sup = R._Supervisor(LimitFrom(start=10 ** 6))
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'}):     # as the rehearsal reaches it (scripted)
            n = _reach_approval(sup, 'q', list(R.SCENARIOS['doors']['lines']))
        sup._interpreter = lambda *a, **k: _limited(sup, 'budget')
        t = sup.turn(project_id='q', account_id='a', message='עוד דבר: יש חניה ליד החנות', lang='he')
        self.assertGreater(n, 0)
        self.assertTrue(t.reply.startswith(HE['limit_budget']), t.reply)
        self.assertIn(HE['limit_ready'], t.reply)
        self.assertIn('approve_spec', [a['type'] for a in t.actions])
        self.assertEqual(t.questions, [])

    def test_a_greeting_after_the_stop_is_not_provider_busy_and_never_repeats(self):
        from omni_prod.intake import lanes
        sup = R._Supervisor(LimitFrom(start=2))
        sup.turn(project_id='g', account_id='a', message=R.SCENARIOS['doors']['lines'][0], lang='he')
        stop = sup.turn(project_id='g', account_id='a', message='יש לנו גם תצוגה בחנות', lang='he')
        free = (None, lanes.choose(lanes.LOW))           # a greeting's free lane: no model, no reservation is tried
        self.assertEqual(free[1]['lane'], lanes.DETERMINISTIC)
        with mock.patch.object(sup, '_classify', return_value=free):
            first = sup.turn(project_id='g', account_id='a', message='תודה', lang='he')
            second = sup.turn(project_id='g', account_id='a', message='תודה', lang='he')
        for t in (first, second):
            self.assertNotIn(HE['model_unavailable'], t.reply)
            self.assertNotIn(HE['rephrase'], t.reply)
            self.assertEqual(t.interpretation['limit'], {'kind': 'budget', 'source': 'closed'})
        # the opening alternates, so no two closing messages in a row are the same (warehouse 113)
        self.assertEqual([t.reply.split('.')[0] for t in (stop, first, second)],
                         [HE[k].split('.')[0] for k in ('limit_budget', 'limit_still', 'limit_still_alt')])

    def test_a_greeting_after_a_daily_pause_says_paused_not_provider_busy(self):
        # the daily limit closes nothing (the next paid message tries again), but a free-lane message in between
        # still says it, not "provider busy"
        from omni_prod.intake import lanes
        sup = R._Supervisor(LimitFrom(start=2, kind='daily'))
        sup.turn(project_id='dg', account_id='a', message=R.SCENARIOS['doors']['lines'][0], lang='he')
        sup.turn(project_id='dg', account_id='a', message='יש לנו גם תצוגה בחנות', lang='he')
        with mock.patch.object(sup, '_classify', return_value=(None, lanes.choose(lanes.LOW))):
            t = sup.turn(project_id='dg', account_id='a', message='תודה', lang='he')
        self.assertEqual(t.interpretation['limit'], {'kind': 'daily', 'source': 'carried'})
        self.assertNotIn(HE['model_unavailable'], t.reply)

    def test_a_closed_conversation_never_pays_a_model_again(self):
        # D10 review: after a long message was refused, a short one would fit under the cap and run after the closing
        class OnlyTheSecond(LimitFrom):
            def interpret(self, message, brief=None):
                out = super().interpret(message, brief)
                if self.calls != 2:
                    out.limit, out.interpreter = None, 'model:scripted'
                return out
        source = OnlyTheSecond(start=2)
        sup = R._Supervisor(source)
        sup.turn(project_id='c', account_id='a', message=R.SCENARIOS['doors']['lines'][0], lang='he')
        sup.turn(project_id='c', account_id='a', message='יש לנו גם תצוגה בחנות', lang='he')
        t = sup.turn(project_id='c', account_id='a', message='כן', lang='he')
        self.assertEqual(source.calls, 2)                        # the paid interpreter was not asked again
        self.assertEqual(t.interpretation['limit'], {'kind': 'budget', 'source': 'closed'})
        self.assertNotIn(HE['model_unavailable'], t.reply)

    def test_the_missing_items_are_named_and_one_is_asked_and_answered_by_words_for_free(self):
        # D10 review (confirmed): naming the gaps alone was a dead end -- the spec tab edits only answered fields and a
        # typed answer is read only against an asked question. Now one open choice question is asked in words, and
        # the next typed message records it with no model call and no reservation.
        lf = LimitFrom(start=1)
        sup = R._Supervisor(lf)
        t = sup.turn(project_id='m', account_id='a', message='אתר לחנות פרחים בחיפה', lang='he')
        self.assertTrue(t.reply.startswith(HE['limit_budget']), t.reply)
        self.assertEqual(t.reply.count('?'), 1, t.reply)                 # exactly one question, never a list
        (qid,) = t.asked_in_words
        stored = [m for m in sup.store.messages_for('m') if m['role'] == 'assistant'][-1]
        self.assertIn(qid, stored['interpretation']['asked'])
        self.assertIn(qid, sup.briefs.latest('m').brief.open_material)
        calls = lf.calls
        nxt = sup.turn(project_id='m', account_id='a', message='כן', lang='he')
        self.assertEqual(lf.calls, calls)                                 # closed: no model was asked
        self.assertNotIn(qid, sup.briefs.latest('m').brief.open_material or ())
        self.assertNotIn(HE['model_unavailable'], nxt.reply)

    def test_the_daily_limit_says_later_not_closed(self):
        sup = R._Supervisor(LimitFrom(start=1, kind='daily'))
        t = sup.turn(project_id='d', account_id='a', message=R.SCENARIOS['doors']['lines'][0], lang='he')
        self.assertTrue(t.reply.startswith(HE['limit_daily']), t.reply)
        self.assertEqual(t.interpretation['limit']['kind'], 'daily')

    def test_the_stored_message_says_limit_and_carries_no_amounts(self):
        sup = R._Supervisor(LimitFrom(start=1))
        sup.turn(project_id='s', account_id='a', message=R.SCENARIOS['doors']['lines'][0], lang='he')
        stored = [m for m in sup.store.messages_for('s') if m['role'] == 'assistant'][-1]
        self.assertTrue(stored['content'].startswith(HE['limit_budget']), stored['content'])
        self.assertEqual(stored['interpretation']['limit'], {'kind': 'budget', 'source': 'reserve'})
        self.assertEqual(_conversation_message_status(stored), 'limit')     # not "built from fixed rules"


def _limited(sup, kind):
    class One(Scripted):
        def interpret(self, message, brief=None):
            out = super().interpret(message, brief)
            out.interpreter, out.limit = 'deterministic', {'kind': kind, 'source': 'reserve'}
            return out
    return One()


class TheQuestionnaireKeepsItsCards(unittest.TestCase):
    """D10 review: an account without the agent answers by buttons, which are free -- at the limit the model stops and
    the cards go on; the conversation is not closed on them."""

    def test_a_questionnaire_account_keeps_its_cards_at_the_limit(self):
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '0', 'OMNI_INTAKE_MODEL': '1'}):
            sup = R._Supervisor(LimitFrom(start=1))
            t = sup.turn(project_id='k', account_id='a', message='אתר לחנות פרחים בחיפה', lang='he')
        self.assertTrue(t.reply.startswith(HE['limit_budget']), t.reply)
        self.assertTrue(t.questions, 'the questionnaire cards are gone')
        self.assertEqual(t.interpretation['limit']['kind'], 'budget')


class TheLimitIsTyped(unittest.TestCase):
    """The real ReservedWorkerInterpreter: a refused reservation is a typed limit, and only {kind, source} leaves."""

    def test_the_project_scope_is_budget_and_the_daily_scope_is_daily(self):
        for scope, kind in (('project:acct:p', 'budget'), (B.DAILY_SCOPE, 'daily')):
            exc = B.BudgetExceeded(scope, Decimal('0.15'), Decimal('0.14'), Decimal('0.035'))
            it = worker_interp(FakeService(reserve_exc=exc)).interpret('אתר לחנות פרחים בחיפה')
            self.assertEqual(it.limit, {'kind': kind, 'source': 'reserve'})
            self.assertNotIn('0.15', str(it.to_dict()['limit']))
            self.assertIn('limit', it.to_dict())

    def test_a_refusal_caused_only_by_calls_in_flight_is_busy_not_closed(self):
        # D10 review: 0.14 counted, of which 0.10 is a turn still executing; the next quote fits once it settles
        exc = B.BudgetExceeded('project:acct:p', Decimal('0.15'), Decimal('0.14'), Decimal('0.035'), Decimal('0.10'))
        self.assertEqual(exc.kind, 'busy')
        self.assertEqual(B.BudgetExceeded('project:acct:p', Decimal('0.15'), Decimal('0.14'), Decimal('0.035')).kind,
                         'budget')

    def test_no_limit_no_key(self):
        it = worker_interp(FakeService(reserve_exc=B.QuoteUnavailable('no price'))).interpret('אתר לחנות פרחים')
        self.assertIsNone(it.limit)
        self.assertNotIn('limit', it.to_dict())


class ThePreCheckSaysItToo(unittest.TestCase):
    """The pre-check (intake.mode) refuses before any reservation when the project has spent its cap: the same closing,
    from source 'precheck', never "provider busy"."""

    def test_a_spent_project_is_closed_at_the_precheck(self):
        class Spent:
            def counted(self, scope):
                return Decimal('0.15') if scope.startswith('project:') else Decimal('0')
        env = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.15',
               'OMNI_INTAKE_DAILY_BUDGET_USD': '1.00'}
        with mock.patch.dict(os.environ, env):
            sup = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), reservations=Spent(),
                                         enqueue=lambda rid: None)
            t = sup.turn(project_id='pc', account_id='acct', message='אתר לחנות פרחים עם משלוחים בחיפה', lang='he')
        self.assertEqual(t.interpretation['limit'], {'kind': 'budget', 'source': 'precheck'})
        self.assertTrue(t.reply.startswith(HE['limit_budget']), t.reply)
        self.assertNotIn(HE['model_unavailable'], t.reply)


if __name__ == '__main__':
    unittest.main()
