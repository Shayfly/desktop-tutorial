"""The conversation agent's turn cap and its usage per conversation, on real PostgreSQL (owner 2026-11-18).

The owner's decision for Sonnet: at most 8 turns per conversation, tokens and cost recorded per conversation. A turn is
a paid call the provider received or may have received; a released call, or a settled call the provider never received
(contacted=false), is not one. Only reservations made under the cap count, so a project's earlier turns never close it
on the first day. The check runs inside reserve(), under the scope locks, so a retry with the same key is never refused.
Real ReservationService on a fresh database with every migration; no provider is called.
"""
import os
import sys
import uuid
from decimal import Decimal

from omni_prod.intake import budget as B

sys.path.insert(0, os.path.dirname(__file__))
from test_intake_budget_pg import PG, PAYLOAD, _quote   # noqa: E402

CAPS = B.Caps(Decimal('1'), Decimal('10'), project_turns=8)
SCOPE = 'project:acct:{}'


class TheTurnCap(PG):
    pool_size = 8

    def take(self, project, *, caps=CAPS, key=None, amount=Decimal('0.004')):
        return self.svc.reserve(idempotency_key=key or uuid.uuid4().hex, account_id='acct', project_id=project,
                                quote_=_quote(amount), caps=caps, payload=PAYLOAD)

    def settle(self, r, *, contacted=True, tokens=(1000, 200), actual=Decimal('0.003')):
        claimed = self.svc.claim(r.id, worker_id='w', lease_seconds=90, max_age_seconds=600)
        self.assertIsNotNone(claimed)
        self.assertTrue(self.svc.mark_executing(claimed, lease_seconds=90))
        metering = {'contacted': contacted, 'input_tokens': tokens[0] if contacted else None,
                    'output_tokens': tokens[1] if contacted else None, 'model': 'claude-sonnet-5-5'}
        if contacted:
            return self.svc.settle(claimed, cost_state=B.CONFIRMED, actual_usd=actual, model='claude-sonnet-5-5',
                                   metering=metering)
        return self.svc.settle(claimed, cost_state=B.CONFIRMED_ZERO, actual_usd=Decimal('0'), metering=metering)

    def test_eight_turns_then_the_ninth_is_refused_and_closes(self):
        p = 'cap8'
        for _ in range(8):
            self.settle(self.take(p))
        with self.assertRaises(B.TurnCapReached) as caught:
            self.take(p)
        self.assertEqual((caught.exception.kind, caught.exception.used, caught.exception.inflight), ('turns', 8, 0))
        self.assertEqual(caught.exception.public(), {'kind': 'turns', 'source': 'reserve'})

    def test_a_call_the_provider_never_received_and_a_released_one_are_not_turns(self):
        p = 'free'
        for _ in range(7):
            self.settle(self.take(p))
        self.settle(self.take(p), contacted=False)                       # refused before the request: not a turn
        self.svc.release(self.take(p).id, reason='queue down')           # never sent: not a turn
        self.settle(self.take(p))                                        # the 8th real turn goes through
        with self.assertRaises(B.TurnCapReached):
            self.take(p)

    def test_calls_still_in_flight_say_busy_not_closed(self):
        p = 'busy'
        for _ in range(7):
            self.settle(self.take(p))
        self.take(p)                                                     # the 8th, reserved, not sent yet
        with self.assertRaises(B.TurnCapReached) as caught:
            self.take(p)
        self.assertEqual(caught.exception.kind, 'busy')

    def test_a_retry_of_the_last_turn_is_its_own_reservation_not_a_refusal(self):
        p = 'retry'
        for _ in range(7):
            self.settle(self.take(p))
        first = self.take(p, key='turn-8')
        again = self.take(p, key='turn-8')
        self.assertEqual(first.id, again.id)

    def test_turns_before_the_cap_existed_do_not_count(self):
        p = 'old'
        for _ in range(10):                                              # the Haiku era: no turn cap
            self.settle(self.take(p, caps=B.Caps(Decimal('1'), Decimal('10'))))
        self.settle(self.take(p))                                        # the first turn under the cap goes through
        r = self.take(p)
        self.assertEqual(r.quote['turn_cap']['used_before'], 1)

    def test_no_cap_no_count(self):
        p = 'none'
        for _ in range(9):
            self.settle(self.take(p, caps=B.Caps(Decimal('1'), Decimal('10'))))
        self.assertNotIn('turn_cap', self.take(p, caps=B.Caps(Decimal('1'), Decimal('10'))).quote)


class TheBudgetHeldInFlight(PG):
    """D10 review: a refusal that only a call still executing causes is 'busy', not a closed conversation."""
    pool_size = 8
    take = TheTurnCap.take
    settle = TheTurnCap.settle

    def test_a_held_quote_refuses_as_busy_and_a_settled_spend_as_budget(self):
        caps = B.Caps(Decimal('0.010'), Decimal('10'))
        self.settle(self.take('held', caps=caps, amount=Decimal('0.004')), actual=Decimal('0.001'))
        self.take('held', caps=caps, amount=Decimal('0.006'))          # in flight: 0.001 settled + 0.006 held
        with self.assertRaises(B.BudgetExceeded) as caught:
            self.take('held', caps=caps, amount=Decimal('0.004'))
        self.assertEqual(caught.exception.kind, 'busy')
        caps2 = B.Caps(Decimal('0.006'), Decimal('10'))
        self.settle(self.take('spent', caps=caps2, amount=Decimal('0.004')), actual=Decimal('0.004'))
        with self.assertRaises(B.BudgetExceeded) as caught:
            self.take('spent', caps=caps2, amount=Decimal('0.004'))
        self.assertEqual(caught.exception.kind, 'budget')


class TheConversationUsage(PG):
    pool_size = 8
    take = TheTurnCap.take
    settle = TheTurnCap.settle

    def test_tokens_and_cost_per_conversation_and_counted_agrees(self):
        p = 'usage'
        self.settle(self.take(p), tokens=(1000, 200), actual=Decimal('0.003'))
        self.settle(self.take(p), tokens=(1500, 300), actual=Decimal('0.004'))
        self.settle(self.take(p), contacted=False)
        u = self.svc.conversation_usage(SCOPE.format(p))
        self.assertEqual((u['turns'], u['input_tokens'], u['output_tokens']), (2, 2500, 500))
        self.assertEqual((u['settled_usd'], u['held_usd'], u['actual_total_usd']),
                         ('0.00700000', '0', '0.00700000'))
        self.assertEqual(Decimal(u['counted_usd']), self.svc.counted(SCOPE.format(p)))
        self.assertEqual(u['models'], ['claude-sonnet-5-5'])

    def test_an_open_or_unknown_call_makes_the_total_unknown_not_zero(self):
        p = 'open'
        self.settle(self.take(p))
        self.take(p)                                                     # in flight
        u = self.svc.conversation_usage(SCOPE.format(p))
        self.assertIsNone(u['actual_total_usd'])
        self.assertEqual((u['open_calls'], u['held_usd']), (1, '0.00400000'))
        self.assertEqual(Decimal(u['counted_usd']), self.svc.counted(SCOPE.format(p)))


class TheReviewFollowUp(PG):
    """D10 review: a call still EXECUTING is in flight (it may settle as not contacted), so the next message reads
    'busy', never 'turns'; a contacted call without reported tokens makes the token totals unknown, never 0; the usage
    states the count the cap itself enforces."""
    pool_size = 8
    take = TheTurnCap.take
    settle = TheTurnCap.settle

    def test_an_executing_eighth_call_is_busy_not_turns(self):
        p = 'exec'
        for _ in range(7):
            self.settle(self.take(p))
        claimed = self.svc.claim(self.take(p).id, worker_id='w', lease_seconds=90, max_age_seconds=600)
        self.assertTrue(self.svc.mark_executing(claimed, lease_seconds=90))
        with self.assertRaises(B.TurnCapReached) as caught:
            self.take(p)
        self.assertEqual((caught.exception.kind, caught.exception.used, caught.exception.inflight), ('busy', 7, 1))

    def test_unreported_tokens_make_the_totals_unknown_and_the_cap_count_is_stated(self):
        p = 'notok'
        self.settle(self.take(p), tokens=(1000, 200))
        self.settle(self.take(p), tokens=(None, None))
        self.take(p)                                                     # in flight
        u = self.svc.conversation_usage(SCOPE.format(p))
        self.assertEqual((u['input_tokens'], u['output_tokens'], u['calls_without_tokens']), (None, None, 1))
        self.assertEqual((u['cap_turns_used'], u['cap_turns_in_flight']), (2, 1))
        self.assertEqual(self.svc.open_held(SCOPE.format(p)), Decimal('0.00400000'))
