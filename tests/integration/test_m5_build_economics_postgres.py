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
            cur.execute(
                "SELECT to_regclass('public.credit_reservations'), "
                "to_regclass('public.creator_subscriptions'), "
                "to_regclass('public.build_request_idempotency')"
            )
            row=cur.fetchone()
        conn.close()
        if not row or None in row[:2]:
            return 'M5 reservation schema not applied'
        if row[2] is None:
            return 'build request idempotency migration 040 not applied'
    except Exception as exc:
        return f'cannot reach live Postgres: {exc}'
    return None


_SKIP=_skip_reason()
if _SKIP is None:
    import psycopg
    from omni_prod.db import DatabasePool
    from omni_prod.job_repository import PostgresBuildRepository
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
                cur.execute(
                    "DELETE FROM build_request_idempotency WHERE account_id=%s", (self.user_id,)
                )
                cur.execute("DELETE FROM build_requests WHERE user_id=%s", (self.user_id,))
                cur.execute("DELETE FROM build_jobs WHERE id = ANY(%s)", (self.build_ids,))
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
                                cost_class='light', credits=1,
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

    def test_failed_build_without_provider_contact_restores_both_balances(self):
        from types import SimpleNamespace
        from omni_prod.worker_tasks import resolve_m5_billing
        from tests.evidence_notice import notice

        service = PostgresSubscriptionService(pool=self.pool)
        before = service.snapshot(self.user_id)
        build_id = self.build_ids[0]
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    decision = service.reserve(
                        cur, build_id=build_id, user_id=self.user_id, project_id='p1',
                        cost_class='light', credits=60,
                        estimated_provider_cost_usd=Decimal('0.35'))
        self.assertTrue(decision.allowed)
        reserved = service.snapshot(self.user_id)
        self.assertEqual(reserved['credits_used'], before['credits_used'] + 60)
        self.assertEqual(Decimal(reserved['provider_spend_usd']),
                         Decimal(before['provider_spend_usd']) + Decimal('0.35'))
        gateway = SimpleNamespace(state=SimpleNamespace(external_calls=0, external_spend_usd=Decimal('0')))
        for _ in range(2):  # retrying settlement cannot refund the same reservation twice
            action, _, _ = resolve_m5_billing(
                service, build_id=build_id, ready=False, gateway=gateway,
                capability_evidence={'usage': []}, economics_quote={'infrastructure_maximum_usd': '0.25'})
            self.assertEqual(action, 'released')
            self.assertEqual(service.snapshot(self.user_id), before)
        with self.pool.connection() as conn:
            status = conn.execute('SELECT status FROM credit_reservations WHERE build_id=%s',
                                  (build_id,)).fetchone()[0]
        self.assertEqual(status, 'RELEASED')
        notice('item2 balances PASS',
               f"before credits={before['credits_remaining']} reserve={before['provider_budget_remaining_usd']}; "
               f"reserved credits={reserved['credits_remaining']} reserve={reserved['provider_budget_remaining_usd']}; "
               f"after credits={before['credits_remaining']} reserve={before['provider_budget_remaining_usd']}; "
               'external_calls=0; replay leaves balances unchanged')

    def test_concurrent_build_request_replays_create_one_durable_build(self):
        repository=PostgresBuildRepository(self.pool)
        barrier=threading.Barrier(2)
        results=[]
        errors=[]
        lock=threading.Lock()
        request_fingerprint='a'*64
        quote_fingerprint='b'*64

        def submit(build_id):
            try:
                barrier.wait(timeout=5)
                with self.pool.connection() as conn:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            created, replay=repository.claim_build_request_idempotency(
                                cur, account_id=self.user_id, internal_project_id='tenant-p1',
                                idempotency_key='concurrent-build-key-1',
                                request_fingerprint=request_fingerprint,
                                quote_fingerprint=quote_fingerprint,
                                quote_fingerprint_version=2, build_id=build_id,
                            )
                            if created:
                                cur.execute(
                                    """
                                    INSERT INTO credit_reservations(
                                        build_id, account_id, project_id, credits_reserved,
                                        estimated_provider_cost_usd, status
                                    ) VALUES (%s, %s, %s, 1, 0, 'RESERVED')
                                    """,
                                    (build_id, self.user_id, 'p1'),
                                )
                                cur.execute(
                                    "INSERT INTO build_jobs(id, project_id, version_id, status) "
                                    "VALUES (%s, 'p1', 'pending', 'queued')",
                                    (build_id,),
                                )
                                cur.execute(
                                    """
                                    INSERT INTO build_requests(build_id, user_id, internal_project_id, prompt)
                                    VALUES (%s, %s, %s, 'integration idempotency test')
                                    """,
                                    (build_id, self.user_id, 'tenant-p1'),
                                )
                with lock:
                    results.append((created, replay if not created else (build_id, 'queued')))
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads=[threading.Thread(target=submit,args=(bid,)) for bid in self.build_ids]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertTrue(all(not thread.is_alive() for thread in threads), 'idempotency race timed out')
        self.assertFalse(errors, errors)
        self.assertEqual(len(results), 2)
        self.assertEqual(sum(created for created, _ in results), 1)
        self.assertEqual(len({build for _, (build, _) in results}), 1)

        conn=psycopg.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM build_request_idempotency "
                "WHERE account_id=%s AND idempotency_key=%s",
                (self.user_id, 'concurrent-build-key-1'),
            )
            self.assertEqual(cur.fetchone()[0], 1)
            cur.execute("SELECT count(*) FROM credit_reservations WHERE account_id=%s", (self.user_id,))
            self.assertEqual(cur.fetchone()[0], 1)
        conn.close()

    def test_caller_key_is_isolated_by_internal_project(self):
        repository=PostgresBuildRepository(self.pool)
        key='shared-project-key-1'
        fingerprints=('c'*64, 'd'*64)
        internal_projects=('tenant-project-a', 'tenant-project-b')
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    for build_id, internal_project in zip(self.build_ids, internal_projects):
                        created, replay=repository.claim_build_request_idempotency(
                            cur, account_id=self.user_id, internal_project_id=internal_project,
                            idempotency_key=key, request_fingerprint=fingerprints[0],
                            quote_fingerprint=fingerprints[1], quote_fingerprint_version=2,
                            build_id=build_id,
                        )
                        self.assertTrue(created)
                        self.assertIsNone(replay)
                        cur.execute(
                            """
                            INSERT INTO credit_reservations(
                                build_id, account_id, project_id, credits_reserved,
                                estimated_provider_cost_usd, status
                            ) VALUES (%s, %s, %s, 1, 0, 'RESERVED')
                            """,
                            (build_id, self.user_id, internal_project),
                        )
                        cur.execute(
                            "INSERT INTO build_jobs(id, project_id, version_id, status) "
                            "VALUES (%s, %s, 'pending', 'queued')",
                            (build_id, internal_project),
                        )
                        cur.execute(
                            """
                            INSERT INTO build_requests(build_id, user_id, internal_project_id, prompt)
                            VALUES (%s, %s, %s, 'project scope test')
                            """,
                            (build_id, self.user_id, internal_project),
                        )
        conn=psycopg.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM build_request_idempotency "
                "WHERE account_id=%s AND idempotency_key=%s",
                (self.user_id, key),
            )
            self.assertEqual(cur.fetchone()[0], 2)
        conn.close()


if __name__ == '__main__':
    unittest.main()
