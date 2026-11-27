"""S6.3 slice 5: a further sketch from the customer's balance, on REAL PostgreSQL.

The owner's answers (2026-11-27, 1א 2א): a further sketch is charged only for NEW wording, and it costs one credit. Real
migrations, the real subscription service (credit_reservations, creator_subscriptions), the real reservation service and the
real execute_reservation; the only double is the provider's HTTP transport behind the real RoutedModelGateway. No paid call.

Proved: the first sketch's words are free and nothing is charged; new words with the free one gone are PRICED and charge nothing
until the customer sends the price they were shown; a wrong price spends nothing; a refusal of the plan reserves nothing; a
written sketch settles its credit with the call's real cost (the sum of settled credit_reservations equals provider_spend_usd,
CLAUDE.md section 5); a failed call gives the credit back; a crash is closed by the reconciler; a double click charges once; the
re-draw with the same words (another colour) is never charged; the owner's own account is never charged."""
from __future__ import annotations

import os
import threading
import unittest
import uuid
from decimal import Decimal
from unittest import mock

import tests.test_direction_sketch_money_pg as M
from omni_prod import discovery as D
from omni_prod.direction_sketch import copy as C
from omni_prod.direction_sketch import funding as F
from omni_prod.direction_sketch import service as SK
from omni_prod.direction_sketch import store as S
from omni_prod.intake import budget as B

SALON = M.SALON
MORE = SALON + ' אנחנו פתוחים בערבים.'          # other words of the customer: the earlier sketch's words no longer fit


class Funding(M.PG):
    plan = 'amateur'

    def setUp(self):
        super().setUp()
        from omni_prod.subscription_store import PostgresSubscriptionService
        self.subs = PostgresSubscriptionService(pool=self.pool)
        self.seed(self.account)

    def seed(self, account, plan=None, used=0):
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO creator_accounts (id, email, password_hash, salt_b64) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                         (account, f'{account}@example.com', 'x', 'x'))
            conn.execute('INSERT INTO creator_subscriptions(user_id, plan_code, cycle, credits_used, provider_spend_usd) '
                         'VALUES (%s, %s, %s, %s, 0) ON CONFLICT DO NOTHING', (account, plan or self.plan, self.subs._cycle_now(), used))
            conn.commit()

    def brief_row(self, text, revision=1):
        brief = D.start(text)
        return type('BriefRow', (), {'brief': brief, 'revision': revision, 'fingerprint': brief.fingerprint()})()

    def create(self, text=SALON, *, price_ack=None, account=None, project=None):
        return SK.create(self.store, self.svc, self.queue.append, self.brief_row(text), account_id=account or self.account,
                         project_id=project or self.project, has_version=False, has_open_build=False, price_ack=price_ack,
                         subscriptions=self.subs, pool=self.pool)

    def view(self, sketch):
        return SK.view(self.store, self.svc, self.store.get(sketch.id, sketch.project_id, sketch.account_id),
                       subscriptions=self.subs, pool=self.pool)

    def first_sketch_written(self):
        """The company's free sketch of the project, asked, answered and shown."""
        sketch, words = self.create()
        self.assertEqual(words['state'], 'pending', words)
        self.run_worker()
        self.assertEqual(self.view(sketch)['state'], 'written')
        return sketch

    def credits(self, account=None):
        return self.sql('SELECT credits_used, provider_spend_usd FROM creator_subscriptions WHERE user_id = %s',
                        (account or self.account,))[0]

    def credit_rows(self, account=None):
        return self.sql('SELECT build_id, status, credits_reserved FROM credit_reservations WHERE account_id = %s ORDER BY created_at',
                        (account or self.account,))


class TheFreeSketchChargesNothing(Funding):
    def test_the_first_sketch_is_free_and_no_credit_row_exists(self):
        self.first_sketch_written()
        self.assertEqual(self.credit_rows(), [])
        self.assertEqual(self.credits(), (0, Decimal('0')))

    def test_a_price_ack_on_the_free_sketch_changes_nothing_but_a_wrong_one_is_refused(self):
        sketch, words = self.create(price_ack=F.PRICE_CREDITS)
        self.assertEqual(words['state'], 'pending')
        self.assertEqual(self.credit_rows(), [])
        with self.assertRaises(F.PriceChanged):
            self.create(MORE, price_ack=7, project=self.project + 'b')
        self.assertEqual(self.credit_rows(), [])

    def test_the_same_words_with_another_colour_is_free_and_never_charged(self):
        first = self.first_sketch_written()
        brief = D.start(SALON)
        brief.fields['color'] = {'value': 'כחול', 'source': 'answer', 'question_id': 'color', 'confidence': 'stated'}
        row = type('BriefRow', (), {'brief': brief, 'revision': 2, 'fingerprint': brief.fingerprint()})()
        second, words = SK.create(self.store, self.svc, self.queue.append, row, account_id=self.account, project_id=self.project,
                                  has_version=False, has_open_build=False, price_ack=F.PRICE_CREDITS, subscriptions=self.subs,
                                  pool=self.pool)
        self.assertEqual((second.copy_from, second.funding, words['state']), (first.id, 'none', 'written'))
        self.assertEqual(self.credit_rows(), [])
        self.assertEqual(self.credits(), (0, Decimal('0')))


class NewWordsAreOneCredit(Funding):
    def test_new_words_say_their_price_and_charge_nothing_until_it_is_acknowledged(self):
        self.first_sketch_written()
        second, words = self.create(MORE)
        self.assertEqual((words['state'], words['price']), ('price_required', {'credits': 1}), words)
        self.assertEqual(self.credit_rows(), [])
        self.assertEqual(self.credits(), (0, Decimal('0')))
        self.assertEqual(second.copy_state, 'none')
        shown = self.view(second)
        self.assertEqual((shown['state'], shown['price']), ('structure', {'credits': 1}))
        self.assertEqual(self.queue, [])

    def test_a_wrong_price_spends_nothing_and_reserves_nothing(self):
        self.first_sketch_written()
        before = self.sql('SELECT count(*) FROM intake_reservations WHERE account_id = %s', (self.account,))[0][0]
        for wrong in (0, 2, 100):
            with self.assertRaises(F.PriceChanged, msg=wrong):
                self.create(MORE, price_ack=wrong)
        self.assertEqual((self.credit_rows(), self.credits()), ([], (0, Decimal('0'))))
        self.assertEqual(self.sql('SELECT count(*) FROM intake_reservations WHERE account_id = %s', (self.account,))[0][0], before)

    def test_the_acknowledged_price_holds_a_credit_and_queues_the_words(self):
        self.first_sketch_written()
        second, words = self.create(MORE, price_ack=F.PRICE_CREDITS)
        self.assertEqual(words['state'], 'pending', words)
        rows = self.credit_rows()
        self.assertEqual([(r[0], r[1], r[2]) for r in rows], [(second.id, 'RESERVED', 1)])
        used, spend = self.credits()
        self.assertEqual(used, 1)
        self.assertGreater(spend, 0)                                           # the quote is held as the provider budget
        stored = self.store.get(second.id, self.project, self.account)
        self.assertEqual((stored.funding, stored.copy_state, stored.credits), ('customer', 'pending', 1))
        scopes = {s for (s,) in self.sql('SELECT scope FROM intake_reservation_scopes WHERE reservation_id = %s', (stored.reservation_id,))}
        self.assertIn(f'sketch-paid:{self.account}:{self.project}', scopes)
        self.assertNotIn(f'sketch-free:{self.account}:{self.project}', scopes - {f'sketch-free:{self.account}:{self.project}'})

    def test_a_written_sketch_charges_its_credit_and_the_books_balance(self):
        self.first_sketch_written()
        second, _ = self.create(MORE, price_ack=F.PRICE_CREDITS)
        self.run_worker()
        shown = self.view(second)
        self.assertEqual((shown['state'], shown['funding']), ('written', 'credits'))
        self.assertEqual([(r[1], r[2]) for r in self.credit_rows()], [('SETTLED', 1)])
        used, spend = self.credits()
        self.assertEqual(used, 1)
        settled = self.sql("SELECT COALESCE(SUM(settled_provider_cost_usd), 0), COALESCE(SUM(actual_provider_cost_usd), 0) "
                           "FROM credit_reservations WHERE account_id = %s AND status = 'SETTLED'", (self.account,))[0]
        self.assertEqual(spend, Decimal(settled[0]))                           # CLAUDE.md section 5: the sum equals provider_spend_usd
        actual = self.sql('SELECT actual_usd FROM intake_reservations WHERE id = %s', (second.reservation_id or
                          self.store.get(second.id, self.project, self.account).reservation_id,))[0][0]
        self.assertEqual(Decimal(settled[1]), Decimal(actual))                 # the call's real cost
        self.assertEqual(self.view(second)['state'], 'written')                # reading again settles nothing twice
        self.assertEqual(self.credits()[0], 1)

    def test_a_failed_call_gives_the_credit_back(self):
        self.first_sketch_written()
        second, _ = self.create(MORE, price_ack=F.PRICE_CREDITS)
        self.run_worker(M.Transport(mode='not_json'))
        shown = self.view(second)
        self.assertEqual(shown['state'], 'failed')
        self.assertEqual([r[1] for r in self.credit_rows()], ['RELEASED'])
        self.assertEqual(self.credits(), (0, Decimal('0')))
        self.assertIsNotNone(shown['price'])                                   # and the customer may try again, for the price

    def test_a_retry_after_a_failure_charges_again_under_its_own_key(self):
        self.first_sketch_written()
        second, _ = self.create(MORE, price_ack=F.PRICE_CREDITS)
        self.run_worker(M.Transport(mode='not_json'))
        self.view(second)
        again, words = self.create(MORE, price_ack=F.PRICE_CREDITS)
        self.assertEqual((again.id, words['state']), (second.id, 'pending'), words)
        self.assertEqual([r[1] for r in self.credit_rows()], ['RELEASED', 'RESERVED'])
        self.run_worker()
        self.assertEqual(self.view(again)['state'], 'written')
        self.assertEqual([r[1] for r in self.credit_rows()], ['RELEASED', 'SETTLED'])
        self.assertEqual(self.credits()[0], 1)

    def test_the_plan_refusing_the_credit_reserves_nothing_and_says_why(self):
        self.first_sketch_written()
        with self.pool.connection() as conn:
            conn.execute('UPDATE creator_subscriptions SET credits_used = 1000000 WHERE user_id = %s', (self.account,))
            conn.commit()
        before = self.sql('SELECT count(*) FROM intake_reservations WHERE account_id = %s', (self.account,))[0][0]
        with self.assertRaises(F.CreditsRefused) as caught:
            self.create(MORE, price_ack=F.PRICE_CREDITS)
        self.assertIn('credits', caught.exception.reason)
        self.assertEqual(self.credit_rows(), [])
        self.assertEqual(self.sql('SELECT count(*) FROM intake_reservations WHERE account_id = %s', (self.account,))[0][0], before)
        sketch = self.store.latest(self.project, self.account)[0]
        self.assertEqual(sketch.copy_state, 'none')                            # the claim was rolled back with the refusal
        self.assertEqual(self.queue, [])

    def test_a_queue_that_is_down_gives_the_credit_back_at_once(self):
        self.first_sketch_written()

        def broken(_):
            raise ConnectionError('redis down')
        sketch, _ = self.create(MORE)
        out = F.request_paid(self.store, self.svc, broken, self.subs, self.pool, sketch,
                             SK._direction_of(sketch), price_ack=F.PRICE_CREDITS)
        self.assertEqual((out['state'], out['reason']), ('failed', 'queue_unavailable'), out)
        self.assertEqual([r[1] for r in self.credit_rows()], ['RELEASED'])
        self.assertEqual(self.credits(), (0, Decimal('0')))

    def test_the_model_being_off_holds_no_credit(self):
        self.first_sketch_written()
        sketch, _ = self.create(MORE)
        with mock.patch.dict(os.environ, {'OMNI_ZERO_COST_MODE': '1'}):
            out = F.request_paid(self.store, self.svc, self.queue.append, self.subs, self.pool, sketch,
                                 SK._direction_of(sketch), price_ack=F.PRICE_CREDITS)
        self.assertEqual(out['state'], 'refused')
        self.assertEqual((self.credit_rows(), self.credits()), ([], (0, Decimal('0'))))

    def test_two_clicks_charge_once(self):
        self.first_sketch_written()
        sketch, _ = self.create(MORE)
        direction = SK._direction_of(sketch)
        outs, barrier = [], threading.Barrier(2)

        def click():
            barrier.wait(timeout=20)
            try:
                outs.append(F.request_paid(self.store, self.svc, self.queue.append, self.subs, self.pool,
                                           self.store.get(sketch.id, self.project, self.account), direction,
                                           price_ack=F.PRICE_CREDITS)['state'])
            except Exception as exc:                                       # the second claim finds the sketch taken
                outs.append(type(exc).__name__)
        threads = [threading.Thread(target=click) for _ in range(2)]
        [t.start() for t in threads]
        [t.join(30) for t in threads]
        self.assertEqual(sorted(outs), ['pending', 'refused'], outs)
        self.assertEqual(len(self.credit_rows()), 1)
        self.assertEqual(self.credits()[0], 1)
        self.assertEqual(len(self.queue), 1)


class ACrashIsClosed(Funding):
    def stale(self, sketch):
        with self.pool.connection() as conn:
            conn.execute("UPDATE direction_sketches SET created_at = now() - interval '10 minutes' WHERE id = %s", (sketch.id,))
            conn.commit()

    def test_a_sketch_held_with_no_call_reserved_fails_and_the_credit_returns(self):
        self.first_sketch_written()
        sketch, _ = self.create(MORE)
        key = F.credit_key(self.pool, sketch.id, new=True)
        self.assertEqual(F._claim_and_hold(self.pool, self.subs, sketch, key, Decimal('0.01')), S.FREE)   # the crash comes next
        self.assertEqual(self.credits()[0], 1)
        self.assertEqual(F.reconcile(self.store, self.svc, self.subs, self.pool), [])                     # too young: left alone
        self.stale(sketch)
        done = F.reconcile(self.store, self.svc, self.subs, self.pool)
        self.assertEqual(done, [{'sketch': sketch.id, 'state': 'failed'}])
        self.assertEqual([r[1] for r in self.credit_rows()], ['RELEASED'])
        self.assertEqual(self.credits()[0], 0)
        self.assertEqual(F.reconcile(self.store, self.svc, self.subs, self.pool), [])                     # once

    def test_a_sketch_whose_call_finished_unseen_is_settled_by_the_reconciler(self):
        self.first_sketch_written()
        second, _ = self.create(MORE, price_ack=F.PRICE_CREDITS)
        self.run_worker()                                                      # nobody reads the sketch: the page was closed
        self.stale(second)
        done = F.reconcile(self.store, self.svc, self.subs, self.pool)
        self.assertEqual(done, [{'sketch': second.id, 'state': 'written'}])
        self.assertEqual([r[1] for r in self.credit_rows()], ['SETTLED'])
        self.assertEqual(self.credits()[0], 1)

    def test_a_call_that_failed_unseen_gives_the_credit_back(self):
        self.first_sketch_written()
        second, _ = self.create(MORE, price_ack=F.PRICE_CREDITS)
        self.run_worker(M.Transport(mode='not_json'))
        self.stale(second)
        self.assertEqual(F.reconcile(self.store, self.svc, self.subs, self.pool), [{'sketch': second.id, 'state': 'failed'}])
        self.assertEqual(([r[1] for r in self.credit_rows()], self.credits()[0]), (['RELEASED'], 0))

    def test_the_janitor_runs_it(self):
        self.first_sketch_written()
        sketch, _ = self.create(MORE)
        F._claim_and_hold(self.pool, self.subs, sketch, F.credit_key(self.pool, sketch.id, new=True), Decimal('0.01'))
        self.stale(sketch)
        from omni_prod import maintenance
        out = maintenance.run_once(pool=self.pool, preview_repo=mock.Mock(mark_expired=lambda: 0), jobs=mock.Mock(),
                                   subscriptions=self.subs, stop_preview=lambda p: None, runtime_host='h')
        self.assertEqual(out.get('sketches'), [{'sketch': sketch.id, 'state': 'failed'}], out)
        self.assertEqual(out['errors'], [])


class TheOwnerIsNeverCharged(Funding):
    def test_every_sketch_of_the_owners_account_is_the_companys_and_never_priced(self):
        from omni_prod import pricing
        owner = pricing.OWNER_ACCOUNT_ID
        self.seed(owner)
        shown = []
        for text in (SALON, MORE, MORE + ' וגם בשישי.'):
            sketch, words = self.create(text, account=owner, price_ack=F.PRICE_CREDITS)
            shown.append((words['state'], self.view(sketch)['price']))
        self.assertEqual(shown, [('pending', None)] * 3)
        self.assertEqual((self.credit_rows(owner), self.credits(owner)), ([], (0, Decimal('0'))))

    def test_a_failed_sketch_of_the_owner_is_never_priced_however_many_calls_failed(self):
        from omni_prod import pricing
        owner = pricing.OWNER_ACCOUNT_ID
        self.seed(owner)
        sketch, _ = self.create(SALON, account=owner)
        for _ in range(F.C.FREE_ATTEMPTS):
            self.run_worker(M.Transport(mode='not_json'))
            self.view(sketch)
            out = C.request(self.store, self.svc, self.queue.append, self.store.get(sketch.id, self.project, owner),
                            SK._direction_of(sketch))
            self.assertEqual(out['state'], 'pending', out)
        self.run_worker(M.Transport(mode='not_json'))
        shown = self.view(sketch)
        self.assertEqual((shown['state'], shown['price']), ('failed', None))
        self.assertEqual(self.credit_rows(owner), [])


if __name__ == '__main__':
    unittest.main()
