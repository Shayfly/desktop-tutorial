"""Issue #12: intake budget reservations on REAL PostgreSQL (and real Redis/RQ
for duplicate delivery). Each class creates a throw-away database, applies the
repository migrations with the production runner and runs real concurrent
transactions. Skipped (reported, never faked) when PostgreSQL is unavailable.
No paid provider call: providers are in-process transports behind the real
RoutedModelGateway, so the gateway's own metering path is exercised."""
from __future__ import annotations

import os
import random
import threading
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from omni_prod.intake import budget as B
from omni_prod.intake import reservation_worker as RW

ROOT = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
REDIS_URL = os.getenv('OMNI_TEST_REDIS_URL', '').strip()
Q1 = Decimal('0.004')                     # a quote unit used by most tests


def _quote(amount=Q1):
    return B.Quote(amount, {'task': 'conversation', 'max_calls': 1, 'max_tokens': 700,
                            'allowed_models': ['gemini-3.1-flash-lite', 'gemini-3.5-flash-lite']})


PAYLOAD = {'system': 'S', 'user': 'מערכת לניהול ציוד', 'max_tokens': 700, 'prompt_version': 'intake-prompt/2-he-first'}


class PG(unittest.TestCase):
    """Fresh database per class with every repository migration applied."""
    pool_size = 70

    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        try:
            import psycopg
            cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        except Exception as exc:
            raise unittest.SkipTest(f'BLOCKED: PostgreSQL unreachable ({type(exc).__name__})')
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        cls.dbname = f'i12_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url, max_size=cls.pool_size, timeout_seconds=60)
        cls.svc = B.ReservationService(cls.pool)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def sql(self, q, args=()):
        with self.pool.connection() as conn:
            with conn.transaction():
                cur = conn.execute(q, args)
                return cur.fetchall() if cur.description else None

    def reserve(self, *, key=None, account='acct', project='p1', caps=None, amount=Q1, lane=B.PRODUCTION,
                campaign=None):
        return self.svc.reserve(idempotency_key=key or uuid.uuid4().hex, account_id=account, project_id=project,
                                quote_=_quote(amount), caps=caps or B.Caps(Decimal('1'), Decimal('10')),
                                payload=PAYLOAD, lane=lane, campaign_id=campaign)

    def pg_deadlocks(self) -> int:
        self.sql('SELECT pg_stat_force_next_flush()')
        time.sleep(0.6)
        self.admin.execute('SELECT pg_stat_clear_snapshot()')
        return int(self.admin.execute('SELECT deadlocks FROM pg_stat_database WHERE datname = %s',
                                      (self.dbname,)).fetchone()[0] or 0)

    def assert_no_deadlocks(self, errors):
        import psycopg
        dead = [e for e in errors if isinstance(e, psycopg.errors.DeadlockDetected)]
        self.assertEqual(dead, [], 'deadlock detected')

    def run_concurrently(self, fns, workers=60):
        results, errors = [], []
        barrier = threading.Barrier(min(workers, len(fns)))

        def wrap(fn):
            try:
                barrier.wait(timeout=30)
            except threading.BrokenBarrierError:
                pass
            try:
                return ('ok', fn())
            except Exception as exc:            # collected and asserted by the caller
                return ('err', exc)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for kind, value in ex.map(wrap, fns):
                (results if kind == 'ok' else errors).append(value)
        return results, errors


# ---------------------------------------------------------------- transports --

class Transport:
    """Stands in for the provider HTTP client behind the REAL RoutedModelGateway."""
    calls = 0
    lock = threading.Lock()

    def __init__(self, mode='ok', input_tokens=900, output_tokens=200, reported=None, sleep=0.0):
        self.mode, self.input_tokens, self.output_tokens, self.reported, self.sleep = \
            mode, input_tokens, output_tokens, reported, sleep
        self.last_usage = None
        self.last_response_model = None

    def complete_json(self, **kw):
        with Transport.lock:
            Transport.calls += 1
        if self.sleep:
            time.sleep(self.sleep)
        from omni_prod.model_gateway import ModelHTTPError
        from omni_prod.provider_usage import ProviderUsage
        if self.mode == 'timeout':
            raise TimeoutError('read timed out')
        if self.mode == 'http429':
            raise ModelHTTPError('HTTP 429 resource exhausted', status=429)
        if self.mode == 'http500_no_usage':
            raise ModelHTTPError('HTTP 500 internal', status=500)
        self.last_usage = ProviderUsage(provider='gemini', model='gemini-3.1-flash-lite', external=True,
                                        request_id=f'req-{uuid.uuid4().hex[:8]}', request_id_source='header',
                                        response_id=None, input_tokens=self.input_tokens,
                                        output_tokens=self.output_tokens, cached_tokens=0,
                                        provider_reported_cost_usd=self.reported, usage_reported=True)
        return {'language': 'he', 'product_family': 'web_app', 'proposals': []}


def gateway_with(transport):
    from omni_prod.model_catalog import parse_model_catalog
    from omni_prod.model_policy import ModelUsePolicy
    from omni_prod.model_router import RoutingPolicy
    from omni_prod.routed_gateway import RoutedModelGateway
    raw = (ROOT / 'infra' / 'worker-host' / 'model-catalog.json').read_text()

    def factory(quoted, models):
        cat = parse_model_catalog(raw, {'GEMINI_API_KEY': 'test-only-not-a-key'})
        ranked = tuple(m for m in cat if m.option.model in models)
        return RoutedModelGateway(ranked=ranked, routing_policy=RoutingPolicy(minimum_quality=70),
                                  policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                        external_budget_usd=quoted, max_external_calls_per_build=1),
                                  transient_retries=0, gateway_factory=lambda endpoint: transport,
                                  sleep=lambda s: None)
    return factory


def real_quote(user='מערכת לניהול ציוד'):
    from omni_prod.intake.interpreter import MAX_OUTPUT_TOKENS, SYSTEM
    return B.quote(system=SYSTEM, user=user, max_tokens=MAX_OUTPUT_TOKENS)


# ------------------------------------------------------------------- tests --

class QuoteTests(unittest.TestCase):
    def test_quote_covers_every_allowed_route_and_fails_closed(self):
        q = real_quote('א' * 4000)
        worst = max(Decimal(m['worst_case_usd']) for m in q.envelope['models'])
        self.assertGreaterEqual(q.amount_usd, worst)
        self.assertEqual((q.envelope['max_calls'], q.envelope['transient_retries']), (1, 0))
        with self.assertRaises(B.QuoteUnavailable):
            B.quote(system='s', user='u', max_tokens=700, models=('no-such-model',))
        with self.assertRaises(B.QuoteUnavailable):
            B.quote(system='s', user='u', max_tokens=0)
        with self.assertRaises(B.QuoteUnavailable):
            B.quote(system='s', user='u', max_tokens=700, max_calls=2)
        os.environ['OMNI_MODEL_CATALOG_JSON'] = '{"not": "a list"}'
        try:
            with self.assertRaises(B.QuoteUnavailable):
                real_quote()
        finally:
            del os.environ['OMNI_MODEL_CATALOG_JSON']

    def test_gateway_worst_case_never_exceeds_the_quote(self):
        q = real_quote('א' * 4000)
        from omni_prod.intake.interpreter import MAX_OUTPUT_TOKENS, SYSTEM
        gw = gateway_with(Transport())(q.amount_usd, tuple(q.envelope['allowed_models']))
        routes = gw.ranked_routes({'system': SYSTEM, 'user': 'א' * 4000, 'max_tokens': MAX_OUTPUT_TOKENS},
                                  'conversation')
        self.assertTrue(routes)
        self.assertTrue(all(r.max_estimated_cost_usd <= q.amount_usd for r, _, _ in routes))


class ConcurrencyTests(PG):
    def test_project_cap_saturation_60_concurrent(self):
        cap = Q1 * 10
        caps = B.Caps(cap, Decimal('100'))
        results, errors = self.run_concurrently([lambda: self.reserve(project='sat', caps=caps)] * 60)
        exceeded = [e for e in errors if isinstance(e, B.BudgetExceeded)]
        self.assert_no_deadlocks(errors)
        self.assertEqual((len(results), len(exceeded), len(errors)), (10, 50, 50))
        self.assertEqual(self.svc.counted('project:acct:sat'), cap)

    def test_daily_cap_across_projects_saturation(self):
        caps = B.Caps(Decimal('1'), Q1 * 7)
        fresh = f'daily-{uuid.uuid4().hex[:6]}'
        self.sql("DELETE FROM intake_reservation_scopes WHERE scope = 'daily:global'")  # isolate from other tests
        fns = [lambda i=i: self.reserve(account=fresh, project=f'proj{i}', caps=caps) for i in range(55)]
        results, errors = self.run_concurrently(fns)
        self.assert_no_deadlocks(errors)
        self.assertEqual(len(results), 7)
        self.assertTrue(all(isinstance(e, B.BudgetExceeded) and e.scope == B.DAILY_SCOPE for e in errors))
        self.assertLessEqual(self.svc.counted(B.DAILY_SCOPE), Q1 * 7)

    def test_campaign_cap_is_isolated_and_hard(self):
        camp = f'acc-{uuid.uuid4().hex[:6]}'
        big = Decimal('0.9')
        caps = B.Caps(project_usd=Decimal('2'), campaign_usd=Decimal('10'))
        fns = [lambda i=i: self.reserve(account='qa', project=f'test{i % 15}', caps=caps, amount=big,
                                        lane=B.CAMPAIGN, campaign=camp) for i in range(60)]
        before_daily = self.svc.counted(B.DAILY_SCOPE)
        results, errors = self.run_concurrently(fns)
        self.assert_no_deadlocks(errors)
        self.assertEqual(len(results), 11)                                 # floor(10 / 0.9)
        self.assertLessEqual(self.svc.counted(f'campaign:{camp}'), Decimal('10'))
        self.assertEqual(self.svc.counted(B.DAILY_SCOPE), before_daily)     # production accounting untouched
        with self.assertRaises(ValueError):                              # campaign lane needs its id
            B.scopes_for('a', 'p', B.CAMPAIGN, None, caps)

    def test_mixed_lifecycle_100_operations_keep_every_cap(self):
        """reserve / claim / execute / settle / release / reconcile interleaved."""
        cap = Q1 * 12
        caps = B.Caps(cap, Decimal('100'))
        acct = f'mix{uuid.uuid4().hex[:6]}'
        rng = random.Random(7)

        def one(i):
            r = self.reserve(account=acct, project='m', caps=caps)
            c = self.svc.claim(r.id, worker_id=f'w{i}')
            if c is None:
                return 'dup'
            action = rng.choice(['settle', 'settle_unknown', 'release', 'zero', 'execute_only'])
            if action == 'release':
                return self.svc.release(c.id, reason='test') and 'released'
            self.assertTrue(self.svc.mark_executing(c))
            if action == 'execute_only':
                return 'executing'
            if action == 'settle_unknown':
                return self.svc.settle(c, cost_state=B.COST_UNKNOWN, actual_usd=None, failure_reason='timeout').state
            if action == 'zero':
                return self.svc.settle(c, cost_state=B.CONFIRMED_ZERO, actual_usd=Decimal('0')).state
            return self.svc.settle(c, cost_state=B.ESTIMATED, actual_usd=Decimal('0.001')).state

        fns = [lambda i=i: one(i) for i in range(100)] + [self.svc.reconcile] * 10
        deadlocks_before = self.pg_deadlocks()
        results, errors = self.run_concurrently(fns, workers=60)
        self.assert_no_deadlocks(errors)
        self.assertEqual(self.pg_deadlocks(), deadlocks_before)          # PostgreSQL's own counter
        self.assertTrue(all(isinstance(e, B.BudgetExceeded) for e in errors), errors[:3])
        self.assertLessEqual(self.svc.counted(f'project:{acct}:m'), cap)
        # recompute from rows: counted == sum of the per-state rule, never above cap
        rows = self.sql("SELECT state, quoted_usd, actual_usd FROM intake_reservations WHERE account_id = %s", (acct,))
        recomputed = sum((Decimal(0) if s == 'RELEASED' else (a if s == 'SETTLED' else q)) for s, q, a in rows)
        self.assertEqual(recomputed, self.svc.counted(f'project:{acct}:m'))

    def test_idempotency_50_concurrent_duplicates(self):
        key = f'dup-{uuid.uuid4().hex}'
        results, errors = self.run_concurrently([lambda: self.reserve(key=key, project='idem')] * 50)
        self.assertEqual(errors, [])
        self.assertEqual(len({r.id for r in results}), 1)
        self.assertEqual(self.sql('SELECT count(*) FROM intake_reservations WHERE idempotency_key = %s', (key,))[0][0], 1)
        with self.assertRaises(B.IdempotencyConflict):
            self.reserve(key=key, project='other-project')

    def test_deadlock_detector_is_live_negative_control(self):
        """Opposite lock order DOES deadlock and IS counted -- so the zero counts
        asserted elsewhere are meaningful."""
        import psycopg
        for scope in ('nc:a', 'nc:b'):
            self.sql("INSERT INTO intake_budget_scopes (scope, kind) VALUES (%s, 'project') ON CONFLICT DO NOTHING", (scope,))
        before = self.pg_deadlocks()
        barrier = threading.Barrier(2)
        errors = []

        def tx(first, second):
            try:
                with psycopg.connect(self.url) as conn:
                    with conn.transaction():
                        conn.execute('SELECT 1 FROM intake_budget_scopes WHERE scope = %s FOR UPDATE', (first,))
                        barrier.wait(timeout=10)
                        conn.execute('SELECT 1 FROM intake_budget_scopes WHERE scope = %s FOR UPDATE', (second,))
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=tx, args=('nc:a', 'nc:b')), threading.Thread(target=tx, args=('nc:b', 'nc:a'))]
        [t.start() for t in threads]
        [t.join(30) for t in threads]
        self.assertEqual(len([e for e in errors if isinstance(e, psycopg.errors.DeadlockDetected)]), 1)
        self.assertEqual(self.pg_deadlocks(), before + 1)

    def test_lock_order_is_global_and_sorted(self):
        """Deadlock-free by construction: every scope-locking transaction takes
        anchors in ascending order. Verify the order the code requests."""
        seen = []

        class Spy:
            def execute(self, sql, args=()):
                if 'FOR UPDATE' in sql and 'intake_budget_scopes' in sql:
                    seen.append(args[0])

            def fetchone(self):
                return ('x',)
        B.ReservationService._lock_scopes(Spy(), ['project:a:p', 'daily:global', 'campaign:x'])
        self.assertEqual(seen, sorted(seen))


class RollingWindowTests(PG):
    def test_24h_boundary(self):
        acct = f'win{uuid.uuid4().hex[:6]}'
        self.sql("DELETE FROM intake_reservation_scopes WHERE scope = 'daily:global'")
        caps = B.Caps(Decimal('1'), Decimal('1'))
        r1 = self.reserve(account=acct, project='w')
        c1 = self.svc.claim(r1.id, worker_id='w')
        self.svc.mark_executing(c1)
        self.svc.settle(c1, cost_state=B.CONFIRMED, actual_usd=Decimal('0.003'))
        old = self.reserve(account=acct, project='w2')                       # never settled: always counted
        now = datetime.now(timezone.utc)
        self.sql('UPDATE intake_reservations SET reserved_at = %s WHERE id = %s', (now - timedelta(hours=24, seconds=1), r1.id))
        self.sql('UPDATE intake_reservations SET reserved_at = %s WHERE id = %s', (now - timedelta(days=3), old.id))
        svc = B.ReservationService(self.pool, clock=now)
        self.assertEqual(svc.counted(B.DAILY_SCOPE), Q1)                     # settled one fell out; open one stays
        self.sql('UPDATE intake_reservations SET reserved_at = %s WHERE id = %s', (now - timedelta(hours=23, minutes=59), r1.id))
        self.assertEqual(svc.counted(B.DAILY_SCOPE), Q1 + Decimal('0.003'))
        self.assertEqual(svc.counted(f'project:{acct}:w'), Decimal('0.003'))  # project cap is not windowed
        del caps


class LifecycleTests(PG):
    def setUp(self):
        Transport.calls = 0

    def test_settle_double_and_wrong_token(self):
        r = self.svc.claim(self.reserve(project='dbl').id, worker_id='w')
        self.svc.mark_executing(r)
        s1 = self.svc.settle(r, cost_state=B.CONFIRMED, actual_usd=Decimal('0.002'))
        s2 = self.svc.settle(r, cost_state=B.CONFIRMED, actual_usd=Decimal('0.002'))   # duplicate: same outcome
        self.assertEqual((s1.state, s2.actual_usd), (B.SETTLED, Decimal('0.002')))
        with self.assertRaises(B.StaleClaim):
            self.svc.settle(r, cost_state=B.CONFIRMED, actual_usd=Decimal('0.003'))   # different outcome
        other = self.svc.claim(self.reserve(project='dbl').id, worker_id='w')
        self.svc.mark_executing(other)
        other.claim_token = 'forged'
        with self.assertRaises(B.StaleClaim):
            self.svc.settle(other, cost_state=B.CONFIRMED, actual_usd=Decimal('0'))
        events = self.sql('SELECT to_state FROM intake_reservation_events WHERE reservation_id = %s ORDER BY id', (r.id,))
        self.assertEqual([e[0] for e in events], ['RESERVED', 'CLAIMED', 'EXECUTING', 'SETTLED'])

    def test_unknown_requires_null_amount_reason_and_evidence_to_release(self):
        r = self.svc.claim(self.reserve(project='unk').id, worker_id='w')
        self.svc.mark_executing(r)
        with self.assertRaises(ValueError):
            self.svc.settle(r, cost_state=B.COST_UNKNOWN, actual_usd=Decimal('0'), failure_reason='x')
        with self.assertRaises(ValueError):
            self.svc.settle(r, cost_state=B.COST_UNKNOWN, actual_usd=None)
        u = self.svc.settle(r, cost_state=B.COST_UNKNOWN, actual_usd=None, failure_reason='timeout')
        self.assertEqual((u.state, u.actual_usd), (B.UNKNOWN, None))
        self.assertEqual(self.svc.counted('project:acct:unk'), Q1)               # full quote held
        self.assertFalse(self.svc.release(r.id, reason='try'))                   # cannot silently release
        with self.assertRaises(ValueError):
            self.svc.resolve_unknown(r.id, cost_state=B.CONFIRMED, actual_usd=Decimal('0.001'), evidence='',
                                     resolved_by='ops')
        done = self.svc.resolve_unknown(r.id, cost_state=B.CONFIRMED, actual_usd=Decimal('0.0011'),
                                        evidence='Gemini billing export 2026-10-11 line 42', resolved_by='ops')
        self.assertEqual((done.state, done.actual_usd), (B.SETTLED, Decimal('0.0011')))
        with self.assertRaises(Exception):   # DB constraint: SETTLED needs an amount
            self.sql("UPDATE intake_reservations SET actual_usd = NULL WHERE id = %s", (r.id,))

    def test_worker_crash_before_provider_releases_after_provider_holds(self):
        before = self.svc.claim(self.reserve(project='crash').id, worker_id='w', lease_seconds=1)
        during = self.svc.claim(self.reserve(project='crash').id, worker_id='w', lease_seconds=1)
        self.svc.mark_executing(during, lease_seconds=1)            # crash after the write-ahead marker
        time.sleep(1.3)
        out = self.svc.reconcile()
        self.assertIn(before.id, out['released'])                   # provider certainly not contacted
        self.assertIn(during.id, out['unknown'])                    # may have been billed
        self.assertEqual(self.svc.get(during.id).state, B.UNKNOWN)
        self.assertIsNone(self.svc.get(during.id).actual_usd)
        self.assertEqual(self.svc.counted('project:acct:crash'), Q1)  # only the uncertain one still held
        self.assertEqual(self.svc.reconcile(), {'unknown': [], 'released': []})   # idempotent
        # a late worker cannot resume an expired lease
        self.assertFalse(self.svc.mark_executing(before))

    def test_provider_outcomes_and_strict_metering(self):
        q = real_quote()
        cases = {
            'ok_tokens': (Transport('ok'), B.SETTLED, B.ESTIMATED),
            'ok_reported': (Transport('ok', reported=Decimal('0.00031')), B.SETTLED, B.CONFIRMED),
            'verified_zero': (Transport('ok', input_tokens=0, output_tokens=0, reported=Decimal('0')),
                              B.SETTLED, B.CONFIRMED_ZERO),
            'timeout': (Transport('timeout'), B.UNKNOWN, B.COST_UNKNOWN),
            'http429_not_assumed_free': (Transport('http429'), B.UNKNOWN, B.COST_UNKNOWN),
            'http500_no_usage': (Transport('http500_no_usage'), B.UNKNOWN, B.COST_UNKNOWN),
        }
        for name, (transport, state, cost_state) in cases.items():
            with self.subTest(name):
                r = self.svc.reserve(idempotency_key=uuid.uuid4().hex, account_id='acct', project_id='outcomes',
                                     quote_=q, caps=B.Caps(Decimal('1'), Decimal('10')),
                                     payload={**PAYLOAD, 'system': 'x'})
                out = RW.execute_reservation(self.pool, r.id, gateway_factory=gateway_with(transport))
                got = self.svc.get(r.id)
                self.assertEqual((got.state, got.cost_state), (state, cost_state), out)
                if cost_state == B.COST_UNKNOWN:
                    self.assertIsNone(got.actual_usd)
                    self.assertTrue(got.failure_reason)
        self.assertEqual(Transport.calls, 6)                          # exactly one provider call each, no retry

    def test_route_above_quote_is_refused_before_contact(self):
        r = self.reserve(project='tiny', amount=Decimal('0.00000100'))
        out = RW.execute_reservation(self.pool, r.id, gateway_factory=gateway_with(Transport()))
        got = self.svc.get(r.id)
        self.assertEqual(Transport.calls, 0)
        self.assertEqual((got.state, got.cost_state, got.actual_usd), (B.SETTLED, B.CONFIRMED_ZERO, Decimal('0')))
        self.assertFalse(out['ok'])

    def test_output_overrun_is_flagged(self):
        r = self.svc.reserve(idempotency_key=uuid.uuid4().hex, account_id='acct', project_id='over', quote_=real_quote(),
                             caps=B.Caps(Decimal('1'), Decimal('10')), payload=PAYLOAD)
        RW.execute_reservation(self.pool, r.id, gateway_factory=gateway_with(Transport(output_tokens=5000)))
        detail = self.sql("SELECT detail FROM intake_reservation_events WHERE reservation_id = %s AND to_state = 'SETTLED'",
                          (r.id,))[0][0]
        self.assertTrue(detail['output_overrun'])

    def test_tenant_isolation(self):
        a = self.reserve(account='tenantA', project='same', caps=B.Caps(Q1, Decimal('10')))
        b = self.reserve(account='tenantB', project='same', caps=B.Caps(Q1, Decimal('10')))   # separate cap
        self.assertNotEqual(a.id, b.id)
        self.assertIsNone(self.svc.get(a.id, account_id='tenantB'))
        self.assertIsNotNone(self.svc.get(a.id, account_id='tenantA'))
        with self.assertRaises(B.BudgetExceeded):
            self.reserve(account='tenantA', project='same', caps=B.Caps(Q1, Decimal('10')))
        with self.assertRaises(ValueError):
            self.reserve(account='tenant:A', project='same')          # scope injection refused

    def test_stale_reserved_is_released_and_late_claim_refused(self):
        r = self.reserve(project='late')
        self.sql("UPDATE intake_reservations SET reserved_at = now() - interval '10 minutes' WHERE id = %s", (r.id,))
        self.assertIsNone(self.svc.claim(r.id, worker_id='w'))                # too old to be useful
        self.assertEqual(self.svc.get(r.id).state, B.RELEASED)


class OutboxAndQueueTests(PG):
    def setUp(self):
        Transport.calls = 0

    def test_outbox_crash_and_replay(self):
        r = self.reserve(project='outbox')
        self.sql("UPDATE intake_outbox SET created_at = now() - interval '1 minute' WHERE reservation_id = %s", (r.id,))
        delivered = []

        def flaky(rid):                         # Redis down on the first pass
            raise ConnectionError('redis down')
        with self.assertRaises(ConnectionError):
            self.svc.relay_once(flaky)
        self.assertIsNone(self.sql('SELECT enqueued_at FROM intake_outbox WHERE reservation_id = %s', (r.id,))[0][0])
        self.assertIn(r.id, self.svc.relay_once(delivered.append))
        self.assertEqual(self.svc.relay_once(delivered.append), [])          # delivered once
        # crash after the enqueue but before the commit: delivered again -> claim dedups
        self.sql('UPDATE intake_outbox SET enqueued_at = NULL WHERE reservation_id = %s', (r.id,))
        self.svc.relay_once(delivered.append)
        self.assertEqual(delivered.count(r.id), 2)
        outs = [RW.execute_reservation(self.pool, rid, gateway_factory=gateway_with(Transport())) for rid in delivered]
        self.assertEqual(sum(1 for o in outs if o.get('skipped')), 1)
        self.assertEqual(Transport.calls, 1)

    def test_concurrent_duplicate_deliveries_invoke_provider_once(self):
        r = self.svc.reserve(idempotency_key=uuid.uuid4().hex, account_id='acct', project_id='dupq', quote_=real_quote(),
                             caps=B.Caps(Decimal('1'), Decimal('10')), payload=PAYLOAD)
        fns = [lambda: RW.execute_reservation(self.pool, r.id, gateway_factory=gateway_with(Transport(sleep=0.05)))] * 50
        results, errors = self.run_concurrently(fns)
        self.assertEqual(errors, [])
        self.assertEqual(Transport.calls, 1)
        self.assertEqual(sum(1 for x in results if x.get('skipped')), 49)

    def test_real_redis_rq_duplicate_jobs(self):
        if not REDIS_URL:
            self.skipTest('BLOCKED: OMNI_TEST_REDIS_URL (real Redis) not configured')
        try:
            import redis
            from rq import Queue, SimpleWorker
        except ImportError as exc:
            self.skipTest(f'BLOCKED: {exc}')
        conn = redis.Redis.from_url(REDIS_URL)
        qname = f'intake-test-{uuid.uuid4().hex[:6]}'
        counter = f'{qname}:provider-calls'
        q = Queue(qname, connection=conn)
        os.environ['I12_TEST_DB_URL'], os.environ['I12_TEST_COUNTER'] = self.url, counter
        r = self.svc.reserve(idempotency_key=uuid.uuid4().hex, account_id='acct', project_id='rq', quote_=real_quote(),
                             caps=B.Caps(Decimal('1'), Decimal('10')), payload=PAYLOAD)
        for _ in range(3):   # API fast path + two relay re-deliveries, same stable job id
            q.enqueue('tests.test_intake_budget_pg.rq_job', r.id, job_id=r.id)
        q.enqueue('tests.test_intake_budget_pg.rq_job', r.id, job_id=f'{r.id}-x')   # even a different job id
        SimpleWorker([q], connection=conn).work(burst=True)
        self.assertEqual(int(conn.get(counter) or 0), 1)                       # provider invoked once
        self.assertEqual(self.svc.get(r.id).state, B.SETTLED)
        executing = self.sql("SELECT count(*) FROM intake_reservation_events WHERE reservation_id = %s "
                             "AND to_state = 'EXECUTING'", (r.id,))[0][0]
        self.assertEqual(executing, 1)
        conn.delete(counter)
        q.delete(delete_jobs=True)


class EndToEndTests(PG):
    """Supervisor -> ReservedWorkerInterpreter -> reservation (real PG) -> worker
    (thread, real RoutedModelGateway, in-process transport) -> settle -> merge."""
    AUTH = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.05',
            'OMNI_INTAKE_DAILY_BUDGET_USD': '0.50', 'OMNI_INTAKE_WAIT_SECONDS': '10'}

    def supervisor(self, transport):
        from omni_prod.conversation.store import MemoryConversationStore
        from omni_prod.conversation.supervisor import ConversationSupervisor
        from tests.test_conversation_os import MemoryBriefs

        def enqueue(rid):   # stands in for RQ: deliver to a worker thread
            threading.Thread(target=RW.execute_reservation, args=(self.pool, rid),
                             kwargs={'gateway_factory': gateway_with(transport)}, daemon=True).start()
        return ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(),
                                      reservations=self.svc, enqueue=enqueue)

    def test_conversation_turn_is_reserved_executed_settled_and_merged(self):
        from unittest import mock
        Transport.calls = 0
        transport = Transport('ok', reported=Decimal('0.00042'))
        sup = self.supervisor(transport)
        with mock.patch.dict(os.environ, self.AUTH):
            t = sup.turn(project_id='e2e', account_id='tenant1', message='מערכת לניהול מלאי למחסן קטן, בעברית',
                         request_key='rk-1', lang='he')
        self.assertEqual(Transport.calls, 1)
        r = self.svc.get(t.reservation_id, account_id='tenant1')
        self.assertEqual((r.state, r.cost_state, r.actual_usd), (B.SETTLED, B.CONFIRMED, Decimal('0.00042')))
        self.assertEqual((t.cost_state, t.cost_usd), ('CONFIRMED', Decimal('0.00042')))
        self.assertTrue(t.interpretation['interpreter'].startswith('model:'))
        self.assertEqual(t.interpretation['lane']['quality_floor'], 70)
        with mock.patch.dict(os.environ, self.AUTH):                       # same request key: no second call
            sup.turn(project_id='e2e', account_id='tenant1', message='מערכת לניהול מלאי למחסן קטן, בעברית',
                     request_key='rk-1', lang='he')
        self.assertEqual(Transport.calls, 1)

    def test_greeting_and_switch_off_never_reserve(self):
        from unittest import mock
        sup = self.supervisor(Transport())
        before = self.sql('SELECT count(*) FROM intake_reservations')[0][0]
        with mock.patch.dict(os.environ, self.AUTH):
            sup.turn(project_id='e2e-g', account_id='tenant1', message='שלום', lang='he')
        with mock.patch.dict(os.environ, {**self.AUTH, 'OMNI_INTAKE_MODEL': '0'}):
            sup.turn(project_id='e2e-g', account_id='tenant1', message='מערכת לניהול מלאי', lang='he')
        self.assertEqual(self.sql('SELECT count(*) FROM intake_reservations')[0][0], before)

    def test_50_concurrent_turns_never_exceed_the_daily_cap(self):
        from unittest import mock
        self.sql("DELETE FROM intake_reservation_scopes WHERE scope = 'daily:global'")
        Transport.calls = 0
        sup = self.supervisor(Transport(sleep=0.05))
        q = real_quote('מערכת לניהול מלאי מספר 00')
        cap = (q.amount_usd * 5).quantize(Decimal('0.00000001'))
        env = {**self.AUTH, 'OMNI_INTAKE_DAILY_BUDGET_USD': str(cap)}

        def turn(i):
            return sup.turn(project_id=f'cc{i}', account_id='tenantC', message=f'מערכת לניהול מלאי מספר {i:02d}',
                            request_key=f'k{i}', lang='he')
        with mock.patch.dict(os.environ, env):
            results, errors = self.run_concurrently([lambda i=i: turn(i) for i in range(50)], workers=50)
        self.assertEqual(errors, [])
        reserved = [t for t in results if t.reservation_id]
        self.assertLessEqual(len(reserved), 5)
        self.assertLessEqual(self.svc.counted(B.DAILY_SCOPE), cap)
        self.assertEqual(Transport.calls, len([t for t in reserved
                                               if self.svc.get(t.reservation_id).state == B.SETTLED]))
        fallback = [t for t in results if not t.reservation_id]
        self.assertTrue(all(t.interpretation['interpreter'] == 'deterministic' for t in fallback))


class MigrationPathTests(unittest.TestCase):
    """036 -> 037 upgrade on a database that already has conversation data."""

    def test_upgrade_preserves_data_and_is_idempotent(self):
        if not DATABASE_URL:
            self.skipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        import psycopg
        from omni_prod.conversation.store import PostgresConversationStore
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        all_m = discover_migrations(ROOT / 'infra' / 'postgres')
        name = f'i12m_{uuid.uuid4().hex[:8]}'
        admin = psycopg.connect(DATABASE_URL, autocommit=True)
        admin.execute(f'CREATE DATABASE {name}')
        url = DATABASE_URL.rsplit('/', 1)[0] + '/' + name
        try:
            with psycopg.connect(url) as conn:
                apply_migrations(conn, [m for m in all_m if m.version <= 36])
            pool = DatabasePool(url, max_size=3)
            old = PostgresConversationStore(pool)
            old.add_message(project_id='p', account_id='a', role='customer', content='שלום', cost_usd=Decimal('0'))
            old.add_message(project_id='p', account_id='a', role='assistant', content='היי', cost_usd=Decimal('0.0012'))
            upto37 = [m for m in all_m if m.version <= 37]   # this test is the 036 -> 037 upgrade (038+ are later)
            with psycopg.connect(url) as conn:
                run = apply_migrations(conn, upto37)
            self.assertEqual(run.applied_versions, (37,))
            with psycopg.connect(url) as conn:
                self.assertEqual(apply_migrations(conn, upto37).applied_versions, ())      # idempotent
            self.assertEqual(old.conversation_cost('p'), Decimal('0.0012'))                 # data intact
            # deterministic writes do not need the new columns; paid writes use them
            old.add_message(project_id='p', account_id='a', role='assistant', content='x', cost_usd=Decimal('0'))
            row = old.add_message(project_id='p', account_id='a', role='assistant', content='y', cost_usd=None,
                                  cost_state='UNKNOWN', reservation_id='irs_x')
            self.assertIsNone(row['cost_usd'])
            self.assertEqual(old.conversation_cost('p'), Decimal('0.0012'))                 # NULL is not $0, not summed
            pool.close()
        finally:
            admin.execute(f'DROP DATABASE IF EXISTS {name} WITH (FORCE)')
            admin.close()


class _CountingTransport(Transport):
    """Counts provider invocations in Redis: RQ may import this module under a
    different name than the test runner, so in-process counters are not shared."""

    def complete_json(self, **kw):
        import redis
        redis.Redis.from_url(REDIS_URL).incr(os.environ['I12_TEST_COUNTER'])
        return super().complete_json(**kw)


def rq_job(reservation_id):
    from omni_prod.db import DatabasePool
    pool = DatabasePool(os.environ['I12_TEST_DB_URL'], max_size=2)
    try:
        return RW.execute_reservation(pool, reservation_id, gateway_factory=gateway_with(_CountingTransport()))
    finally:
        pool.close()


if __name__ == '__main__':
    unittest.main()
