"""The agent's 8-turn cap and its usage record, wired through the supervisor (owner 2026-11-18).

The cap is a condition of the Sonnet approval: agent accounts only. A refused turn is a typed limit ('turns' closes,
'busy' -- the cap reached only by calls still in flight -- does not). The conversation's tokens and cost are stored with
each paid or limited assistant message, on the server: never sent to the browser, and a failure to read them never
fails the turn. The counting itself runs on real PostgreSQL (tests/test_conversation_turn_cap_pg.py); here the real
supervisor and the real ReservedWorkerInterpreter run with a reservation service that is a fake.
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
from omni_prod.intake import conversation_agent as agent

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_limit import LimitFrom                 # noqa: E402
from test_conversation_os import MemoryBriefs                 # noqa: E402
from test_intake_worker_route import FakeService, interp as worker_interp   # noqa: E402

HE = _TXT['he']
AUTH = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.15',
        'OMNI_INTAKE_DAILY_BUDGET_USD': '1.00', 'OMNI_INTAKE_AGENT': 'accounts', 'OMNI_INTAKE_AGENT_ACCOUNTS': 'owner'}


class Svc:
    """Counts nothing; records the caps each reservation was asked under; reports a usage."""
    def __init__(self, usage=None, usage_exc=None):
        self.caps, self.usage, self.usage_exc = [], usage, usage_exc

    def counted(self, scope):
        return Decimal('0')

    def conversation_usage(self, scope):
        if self.usage_exc:
            raise self.usage_exc
        return dict(self.usage or {'turns': 1, 'settled_usd': '0', 'held_usd': '0.035', 'counted_usd': '0.035',
                                   'unknown_calls': 0, 'open_calls': 1, 'actual_total_usd': None,
                                   'input_tokens': 0, 'output_tokens': 0, 'calls_without_tokens': 0, 'models': []})

    def reserve(self, **kw):
        self.caps.append(kw['caps'])
        raise B.TurnCapReached(f"project:{kw['account_id']}:{kw['project_id']}", 8, 8, 0)


class TheCapIsTheAgents(unittest.TestCase):
    def interpreter_caps(self, account):
        with mock.patch.dict(os.environ, AUTH):
            sup = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), reservations=Svc(),
                                         enqueue=lambda rid: None)
            token = agent.for_account(account)
            try:
                return sup._interpreter('p', account).caps
            finally:
                agent.release(token)

    def test_the_agent_account_reserves_under_the_8_turn_cap(self):
        self.assertEqual(self.interpreter_caps('owner').project_turns, agent.MAX_TURNS)
        self.assertEqual(agent.MAX_TURNS, 8)

    def test_every_other_account_has_no_turn_cap(self):
        self.assertIsNone(self.interpreter_caps('someone-else').project_turns)


class TheRefusalIsTyped(unittest.TestCase):
    def test_a_cap_refusal_is_a_turns_limit_and_in_flight_is_busy(self):
        for used, inflight, kind in ((8, 0, 'turns'), (7, 1, 'busy')):
            exc = B.TurnCapReached('project:acct:p', 8, used, inflight)
            it = worker_interp(FakeService(reserve_exc=exc)).interpret('אתר לחנות פרחים בחיפה')
            self.assertEqual(it.limit, {'kind': kind, 'source': 'reserve'})

    def test_bad_caps_are_refused(self):
        for bad in (0, -1, True, 8.0, '8'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                B.Caps(Decimal('1'), Decimal('1'), project_turns=bad)


class TheSupervisorSaysIt(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1', 'OMNI_INTAKE_MODEL': '1'})
        p.start()
        self.addCleanup(p.stop)

    def test_the_turn_cap_closes_the_conversation(self):
        sup = R._Supervisor(LimitFrom(start=1, kind='turns'))
        t = sup.turn(project_id='t', account_id='a', message=R.SCENARIOS['doors']['lines'][0], lang='he')
        self.assertTrue(t.reply.startswith(HE['limit_turns']), t.reply)
        self.assertEqual(t.interpretation['limit'], {'kind': 'turns', 'source': 'reserve'})

    def test_busy_is_not_a_closing_and_is_not_carried(self):
        sup = R._Supervisor(LimitFrom(start=1, kind='busy'))
        t = sup.turn(project_id='b', account_id='a', message=R.SCENARIOS['doors']['lines'][0], lang='he')
        self.assertTrue(t.reply.startswith(HE['limit_busy']), t.reply)
        self.assertNotIn('edit_requirements', [a['type'] for a in t.actions])
        self.assertIsNone(sup._turn_limit('b', type('I', (), {'interpreter': 'deterministic', 'limit': None})(), {}))


class TheUsageIsRecorded(unittest.TestCase):
    def turn(self, svc):
        with mock.patch.dict(os.environ, AUTH):
            sup = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), reservations=svc,
                                         enqueue=lambda rid: None)
            t = sup.turn(project_id='u', account_id='owner', message='אתר לחנות פרחים עם משלוחים בחיפה', lang='he')
        stored = [m for m in sup.store.messages_for('u') if m['role'] == 'assistant'][-1]
        return t, stored

    def test_the_usage_is_stored_with_the_message_and_never_sent_to_the_browser(self):
        t, stored = self.turn(Svc())
        self.assertEqual(stored['interpretation']['usage']['held_usd'], '0.035')
        self.assertEqual(stored['interpretation']['usage']['max_turns'], 8)
        self.assertNotIn('usage', t.to_dict('he')['interpretation'] or {})

    def test_a_usage_failure_never_fails_the_turn(self):
        t, stored = self.turn(Svc(usage_exc=RuntimeError('db down')))
        self.assertEqual(stored['interpretation']['usage'], {'usage_error': 'RuntimeError'})
        self.assertTrue(t.reply)


if __name__ == '__main__':
    unittest.main()
