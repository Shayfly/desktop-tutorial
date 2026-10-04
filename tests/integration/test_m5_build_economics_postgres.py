from __future__ import annotations

import os
import threading
import unittest
import uuid
from decimal import Decimal

DATABASE_URL = os.environ.get('M5_DATABASE_URL', os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test'))


def _skip_reason():
    try:
        import psycopg
    except ImportError as exc:
        return f'psycopg not importable ({exc})'
    try:
        conn=psycopg.connect(DATABASE_URL, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.credit_reservations'), to_regclass('public.creator_subscriptions')")
            row=cur.fetchone()
        conn.close()
        if not row or None in row:
            return 'M5 reservation schema not applied'
    except Exception as exc:
        return f'cannot reach live Postgres: {exc}'
    return None


_SKIP=_skip_reason()
if _SKIP is None:
    import psycopg
    from omni_prod.db import DatabasePool
    from omni_prod.subscription_store import PostgresSubscriptionService


@unittest.skipIf(_SKIP is not None, _SKIP or '')
class RealPostgresReservationConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.user_id='usr_m5econ_'+uuid.uuid4().hex[:12]
        self.build_ids=['bld_'+uuid.uuid4().hex, 'bld_'+uuid.uuid4().hex]
        self.pool=DatabasePool(DATABASE_URL, min_size=1, max_size=4).open()
        conn=psycopg.connect(DATABASE_URL)
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creator_accounts(id,email,password_hash,salt_b64,created_at) VALUES(%s,%s,'x','eA==',now())",
                    (self.user_id, f'{self.user_id}@example.com'),
                )
                cur.execute(
                    "INSERT INTO creator_subscriptions(user_id,plan_code,cycle,credits_used,provider_spend_usd) VALUES(%s,'basic',to_char(now(),'YYYY-MM'),0,0)",
                    (self.user_id,),
                )
        conn.close()

    def tearDown(self):
        conn=psycopg.connect(DATABASE_URL)
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute('DELETE FROM credit_reservations WHERE account_id=%s', (self.user_id,))
                cur.execute('DELETE FROM creator_subscriptions WHERE user_id=%s', (self.user_id,))
                cur.execute('DELETE FROM creator_accounts WHERE id=%s', (self.user_id,))
        conn.close()
        self.pool.close()

    def test_two_concurrent_reservations_cannot_oversubscribe_same_budget(self):
        service=PostgresSubscriptionService(pool=self.pool)
        barrier=threading.Barrier(2)
        results=[]
        errors=[]
        lock=threading.Lock()

        def reserve(build_id):
            try:
                barrier.wait(timeout=5)
                with self.pool.connection() as conn:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            decision=service.reserve(
                                cur, build_id=build_id, user_id=self.user_id, project_id='p1',
                                cost_class='standard', credits=1,
                                estimated_provider_cost_usd=Decimal('1.60'),
                            )
                with lock:
                    results.append(decision.allowed)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads=[threading.Thread(target=reserve,args=(bid,)) for bid in self.build_ids]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        self.assertFalse(errors, errors)
        self.assertEqual(sorted(results), [False, True])

        conn=psycopg.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute('SELECT provider_spend_usd FROM creator_subscriptions WHERE user_id=%s', (self.user_id,))
            spend=Decimal(str(cur.fetchone()[0]))
            cur.execute("SELECT count(*) FROM credit_reservations WHERE account_id=%s AND status='RESERVED'", (self.user_id,))
            reservations=cur.fetchone()[0]
        conn.close()
        self.assertEqual(spend, Decimal('1.60'))
        self.assertEqual(reservations, 1)


if __name__ == '__main__':
    unittest.main()
