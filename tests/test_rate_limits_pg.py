"""Rate limits on the real routes and a real PostgreSQL (the owner's approval, 2026-11-26; omni_prod/rate_limits.py).

The real app twice: omni_prod/investor_app.py is loaded as two separate modules -- two app objects, two connection pools,
two limiters, the code and the database shared -- which is what two Vercel instances are. Requests go through FastAPI's
TestClient into the real middleware and the real route handlers; the counters are the rows of migration 047 in a fresh
database with every repository migration applied. Each limit is pushed to its stated count and one past it.

The limiter's clock is a fake each test moves (the windows are 10 minutes to an hour long); the store, the SQL, the
routes and the password hashing are real. No model, no provider and no network outside the local database are touched.
Needs M4D2_DATABASE_URL (the intake-budget-pg job runs it, in its own process); skipped -- never faked -- without it.
"""
from __future__ import annotations

import importlib.util
import itertools
import logging
import os
import statistics
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
SECRET = 'rate-limits-pg-test-secret-' + 'k' * 40
PASSWORD = 'correct-horse-battery'
WRONG = 'wrong-password-12'
T0 = 2_000_000_000.0                       # the fake clock's first reading; each test starts a day and more later


def _problem() -> str | None:
    if not DATABASE_URL:
        return 'BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured'
    try:
        import fastapi  # noqa: F401
        import psycopg
    except ImportError as exc:
        return f'BLOCKED: {exc.name} is not installed'
    try:
        psycopg.connect(DATABASE_URL, connect_timeout=5).close()
    except Exception as exc:
        return f'BLOCKED: PostgreSQL unreachable ({type(exc).__name__})'
    return None


PROBLEM = _problem()


class Clock:
    def __init__(self, t: float) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def load_instance(name: str):
    """The real investor_app module, executed again under its own name: one more serverless instance."""
    spec = importlib.util.spec_from_file_location(f'omni_prod._rate_limits_instance_{name}',
                                                  ROOT / 'omni_prod' / 'investor_app.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Database(unittest.TestCase):
    """A fresh database with every repository migration applied, for the class."""

    @classmethod
    def setUpClass(cls):
        if PROBLEM:
            raise unittest.SkipTest(PROBLEM)
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        cls.dbname = f'rl_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def sql(self, query, args=()):
        with self.pool.connection() as conn:
            with conn.transaction():
                cur = conn.execute(query, args)
                return cur.fetchall() if cur.description else cur.rowcount


class TwoInstancesOneDatabase(_Database):
    _numbers = itertools.count(1)
    _start = T0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = mock.patch.dict(os.environ, {'OMNI_CREATOR_PERSISTENCE': 'postgres', 'OMNI_DATABASE_URL': cls.url,
                                               'OMNI_SECRET_KEY': SECRET})
        cls.env.start()
        for name in ('OMNI_ENV', 'VERCEL', 'OMNI_S3_ENDPOINT', 'OMNI_REDIS_URL'):
            os.environ.pop(name, None)
        cls.a, cls.b = load_instance('a'), load_instance('b')
        assert cls.a.app is not cls.b.app and cls.a._rate_limiter is not cls.b._rate_limiter
        assert cls.a._v28_pool is not None and cls.b._v28_pool is not None

    @classmethod
    def tearDownClass(cls):
        for instance in (cls.a, cls.b):
            instance._v28_pool.close()
        cls.env.stop()
        super().tearDownClass()

    def setUp(self):
        type(self)._start += 100_000          # every window of the test before has expired; no counter is shared
        self.clock = Clock(type(self)._start)
        self.a._rate_limiter.clock = self.clock
        self.b._rate_limiter.clock = self.clock

    # ---- helpers
    def ip(self) -> str:
        n = next(self._numbers)
        return f'10.{n // 65536 % 256}.{n // 256 % 256}.{n % 256}'

    def email(self) -> str:
        return f'rl-{uuid.uuid4().hex[:12]}@example.com'

    def client(self, instance, ip: str | None = None):
        from fastapi.testclient import TestClient
        return TestClient(instance.app, client=(ip or self.ip(), 40000))

    def register(self, instance=None, ip=None, email=None) -> tuple[str, str]:
        email = email or self.email()
        r = self.client(instance or self.a, ip).post('/api/v28/auth/register', json={'email': email, 'password': PASSWORD})
        self.assertEqual(r.status_code, 200, r.text)
        return email, r.json()['token']

    def assert_refused(self, r, limit: str) -> int:
        self.assertEqual(r.status_code, 429, r.text)
        detail = r.json()['detail']
        self.assertEqual((detail['error'], detail['limit']), ('rate_limited', limit))
        wait = int(r.headers['Retry-After'])
        self.assertGreaterEqual(wait, 1)
        self.assertEqual(detail['retry_after_seconds'], wait)
        self.assertEqual(sorted(detail['messages']), ['ar', 'en', 'he'])
        self.assertEqual(detail['message'], detail['messages']['he'])          # no ?lang=, no Accept-Language
        self.assertEqual(r.headers['Cache-Control'], 'no-store')
        return wait

    def assert_passed(self, r, *statuses):
        self.assertIn(r.status_code, statuses, r.text)

    # ---- each limit at its stated count, and one past it ------------------------------------------------------------
    def test_login_per_identifier_trips_at_ten_across_two_instances(self):
        email = self.email()
        a, b = self.client(self.a), self.client(self.b)            # two instances, two addresses, one e-mail
        for i in range(10):
            self.assert_passed((a, b)[i % 2].post('/api/v28/auth/login', json={'email': email, 'password': WRONG}), 401)
        self.assert_refused(a.post('/api/v28/auth/login', json={'email': email, 'password': WRONG}), 'login_identifier')
        self.assert_refused(b.post('/api/v28/auth/login', json={'email': email, 'password': WRONG}), 'login_identifier')
        self.assert_passed(b.post('/api/v28/auth/login', json={'email': self.email(), 'password': WRONG}), 401)

    def test_login_per_address_trips_at_fifty(self):
        ip = self.ip()
        a, b = self.client(self.a, ip), self.client(self.b, ip)
        for i in range(50):
            self.assert_passed((a, b)[i % 2].post('/api/v28/auth/login', json={'email': self.email(), 'password': WRONG}),
                               401)
        self.assert_refused(a.post('/api/v28/auth/login', json={'email': self.email(), 'password': WRONG}), 'login_ip')

    def test_registration_per_address_trips_at_ten(self):
        ip = self.ip()
        for i in range(10):
            self.register((self.a, self.b)[i % 2], ip)
        r = self.client(self.b, ip).post('/api/v28/auth/register', json={'email': self.email(), 'password': PASSWORD})
        self.assert_refused(r, 'register_ip')

    def test_registration_counts_against_the_login_limit_of_its_e_mail(self):
        email, _ = self.register()
        for _ in range(9):                    # registering an existing e-mail signs in with the password typed
            r = self.client(self.b).post('/api/v28/auth/register', json={'email': email, 'password': WRONG})
            self.assert_passed(r, 409)
        self.assert_refused(self.client(self.a).post('/api/v28/auth/login', json={'email': email, 'password': PASSWORD}),
                            'login_identifier')

    def test_password_reset_per_identifier_trips_at_five(self):
        email, _ = self.register()
        c = self.client(self.a)
        for _ in range(5):
            self.assert_passed(c.post('/api/v28/auth/password-reset/request', json={'email': email}), 202)
        self.assert_refused(c.post('/api/v28/auth/password-reset/request', json={'email': email.upper()}),
                            'password_reset_identifier')

    def test_password_reset_per_address_counts_every_request_and_trips_at_twenty(self):
        ip = self.ip()
        for i in range(20):                   # no e-mail in the body: the route answers 422, the address still counts
            r = self.client((self.a, self.b)[i % 2], ip).post('/api/v28/auth/password-reset/request', json={'x': i})
            self.assert_passed(r, 422)
        r = self.client(self.a, ip).post('/api/v28/auth/password-reset/request', json={'email': self.email()})
        self.assert_refused(r, 'password_reset_ip')

    def test_verification_sends_per_account_trip_at_five(self):
        _, token = self.register()
        auth = {'Authorization': f'Bearer {token}'}
        for i in range(5):
            r = self.client((self.a, self.b)[i % 2]).post('/api/v28/auth/email-verification/request', headers=auth)
            self.assert_passed(r, 202)
        r = self.client(self.a).post('/api/v28/auth/email-verification/request', headers=auth)
        self.assert_refused(r, 'verification_send_account')

    def test_one_time_tokens_per_address_trip_at_thirty(self):
        ip = self.ip()
        for i in range(30):
            route = ('/api/v28/auth/verify-email', '/api/v28/auth/password-reset/confirm')[i % 2]
            r = self.client((self.a, self.b)[i % 2], ip).post(route, json={'token': uuid.uuid4().hex,
                                                                          'new_password': PASSWORD})
            self.assert_passed(r, 400)
        r = self.client(self.b, ip).post('/api/v28/auth/verify-email', json={'token': uuid.uuid4().hex})
        self.assert_refused(r, 'one_time_token_ip')

    def test_routes_that_protect_no_account_carry_no_limit(self):
        _, token = self.register()             # the owner, 2026-11-26 10:01: no customer limit that is not money
        auth = {'Authorization': f'Bearer {token}'}
        before = self.sql('SELECT count(*) FROM rate_limit_counters')[0][0]
        for path, body in (('/api/v28/projects/prj_absent/conversation', {'message': 'hello'}),
                           ('/api/v28/projects/prj_absent/builds', {'prompt': 'a site'}),
                           ('/api/v28/projects/prj_absent/versions/v1/modifications', {'followup': 'bigger title'})):
            for _ in range(3):
                self.assertNotEqual(self.client(self.a).post(path, json=body, headers=auth).status_code, 429)
        self.assertEqual(self.sql('SELECT count(*) FROM rate_limit_counters')[0][0], before)

    def test_the_deployment_status_names_the_store_and_a_missing_047(self):
        self.assertEqual(self.client(self.a).get('/api/v28/deployment').json()['rate_limits'],
                         {'store': 'postgres', 'status': 'OK', 'migration': '047_rate_limits'})
        self.hide_the_table()
        with self.assertLogs('omni_prod.rate_limits', 'ERROR'):
            got = self.client(self.b).get('/api/v28/deployment').json()['rate_limits']
        self.assertEqual((got['status'], got['migration']), ('MIGRATION_MISSING', '047_rate_limits'))
        self.assertIn('infra/postgres/047_rate_limits.sql', got['detail'])

    def test_a_route_with_no_limit_writes_no_counter(self):
        before = self.sql('SELECT count(*) FROM rate_limit_counters')[0][0]
        self.assertEqual(self.client(self.a).get('/api/v28/pricing').status_code, 200)
        self.assertEqual(self.sql('SELECT count(*) FROM rate_limit_counters')[0][0], before)

    # ---- the window ---------------------------------------------------------------------------------------------------
    def test_the_limit_resets_once_the_window_has_passed(self):
        email, c = self.email(), self.client(self.a)
        for _ in range(10):
            self.assert_passed(c.post('/api/v28/auth/login', json={'email': email, 'password': WRONG}), 401)
        first = self.assert_refused(c.post('/api/v28/auth/login', json={'email': email, 'password': WRONG}),
                                    'login_identifier')
        self.assertGreater(first, 15 * 60 // 2)                    # the whole window is not over in a moment
        self.clock.t += first // 2                                  # half way: still refused, and the wait is restated
        second = self.assert_refused(self.client(self.b).post('/api/v28/auth/login', json={'email': email,
                                                                                            'password': WRONG}),
                                     'login_identifier')
        self.clock.t += second
        self.assert_passed(c.post('/api/v28/auth/login', json={'email': email, 'password': WRONG}), 401)

    # ---- the client address -------------------------------------------------------------------------------------------
    SPOOF = ('x-forwarded-for', 'x-real-ip', 'x-vercel-forwarded-for', 'forwarded', 'true-client-ip', 'cf-connecting-ip',
             'x-client-ip')

    def spoofed(self) -> dict:
        fake = f'192.0.2.{next(self._numbers) % 250 + 1}'
        return {h: (f'for={fake}' if h == 'forwarded' else fake) for h in self.SPOOF}

    def test_off_vercel_a_spoofed_forwarding_header_does_not_change_the_identity(self):
        ip = self.ip()
        for i in range(30):                   # a new forged address in every forwarding header, every time
            r = self.client((self.a, self.b)[i % 2], ip).post('/api/v28/auth/verify-email',
                                                              json={'token': uuid.uuid4().hex}, headers=self.spoofed())
            self.assert_passed(r, 400)
        r = self.client(self.a, ip).post('/api/v28/auth/verify-email', json={'token': uuid.uuid4().hex},
                                         headers=self.spoofed())
        self.assert_refused(r, 'one_time_token_ip')

    def test_on_vercel_the_edge_address_counts_and_the_clients_own_headers_do_not(self):
        edge = self.ip()                      # what Vercel's edge writes in x-real-ip
        with mock.patch.dict(os.environ, {'VERCEL': '1'}):
            for i in range(30):               # every request through another Vercel proxy, each forging the rest
                headers = {**self.spoofed(), 'x-real-ip': edge}
                r = self.client((self.a, self.b)[i % 2]).post('/api/v28/auth/verify-email',
                                                              json={'token': uuid.uuid4().hex}, headers=headers)
                self.assert_passed(r, 400)
            r = self.client(self.b).post('/api/v28/auth/verify-email', json={'token': uuid.uuid4().hex},
                                         headers={**self.spoofed(), 'x-real-ip': edge})
            self.assert_refused(r, 'one_time_token_ip')
            r = self.client(self.a).post('/api/v28/auth/verify-email', json={'token': uuid.uuid4().hex},
                                         headers={**self.spoofed(), 'x-real-ip': self.ip()})
            self.assert_passed(r, 400)        # another client behind the same proxy is not counted with the first

    # ---- account enumeration ------------------------------------------------------------------------------------------
    def test_login_answers_the_same_for_a_known_and_an_unknown_e_mail(self):
        known, _ = self.register()
        suspended, _ = self.register()
        self.sql("UPDATE creator_accounts SET account_status = 'SUSPENDED' WHERE email = %s", (suspended,))
        unknown = self.email()
        c = self.client(self.a)
        c.post('/api/v28/auth/login', json={'email': self.email(), 'password': WRONG})       # warm the pool
        answers, times = {}, {'known': [], 'unknown': [], 'suspended': []}
        for _ in range(7):                    # interleaved, so a slow moment of the machine hits all three
            for kind, email in (('known', known), ('unknown', unknown), ('suspended', suspended)):
                started = time.perf_counter()
                r = c.post('/api/v28/auth/login', json={'email': email, 'password': WRONG})
                times[kind].append(time.perf_counter() - started)
                answers.setdefault(kind, set()).add((r.status_code, r.text))
        self.assertEqual(answers['known'], {(401, '{"detail":"invalid credentials"}')})
        self.assertEqual(answers['unknown'], answers['known'])
        self.assertEqual(answers['suspended'], answers['known'])
        medians = {k: statistics.median(v) for k, v in times.items()}
        self.assertLess(max(medians.values()) / min(medians.values()), 1.5, medians)

    def test_a_password_reset_answers_the_same_for_a_known_and_an_unknown_e_mail(self):
        known, _ = self.register()
        c = self.client(self.a)
        answers, times = {'known': set(), 'unknown': set()}, {'known': [], 'unknown': []}
        for _ in range(5):
            for kind in ('known', 'unknown'):
                started = time.perf_counter()
                r = c.post('/api/v28/auth/password-reset/request', json={'email': known if kind == 'known' else self.email()})
                times[kind].append(time.perf_counter() - started)
                answers[kind].add((r.status_code, r.text))
        self.assertEqual(answers['known'], {(202, '{"accepted":true}')})
        self.assertEqual(answers['unknown'], answers['known'])
        written = self.sql("SELECT count(*) FROM creator_identity_tokens t JOIN creator_accounts a ON a.id = t.user_id "
                           "WHERE a.email = %s AND t.purpose = 'PASSWORD_RESET'", (known,))[0][0]
        self.assertEqual(written, 5)          # the work does differ: a token row for the known e-mail only ...
        self.assertGreaterEqual(min(min(v) for v in times.values()), 0.45, times)   # ... and no answer comes sooner
        self.assertLess(abs(statistics.median(times['known']) - statistics.median(times['unknown'])), 0.1, times)

    # ---- when the store cannot answer ---------------------------------------------------------------------------------
    def hide_the_table(self):
        self.sql('ALTER TABLE rate_limit_counters RENAME TO rate_limit_counters_hidden')
        self.addCleanup(self.sql, 'ALTER TABLE IF EXISTS rate_limit_counters_hidden RENAME TO rate_limit_counters')

    def test_without_the_store_sign_in_fails_closed_with_a_503_in_three_languages(self):
        email, _ = self.register()
        self.hide_the_table()
        c = self.client(self.a)
        with self.assertLogs('omni_prod.rate_limits', 'ERROR') as logs:
            r = c.post('/api/v28/auth/login?lang=ar', json={'email': email, 'password': PASSWORD})
        self.assertEqual(r.status_code, 503, r.text)
        detail = r.json()['detail']
        self.assertEqual(detail['error'], 'rate_limit_unavailable')
        self.assertEqual(sorted(detail['messages']), ['ar', 'en', 'he'])
        self.assertEqual(detail['message'], detail['messages']['ar'])
        self.assertEqual(r.headers['Retry-After'], '60')
        self.assertNotIn('148ai_session', r.headers.get('set-cookie', ''))          # the handler did not run
        self.assertIn('refused with 503', '\n'.join(logs.output))
        self.assertIn('migration 047_rate_limits', '\n'.join(logs.output))          # the missing table is named
        self.assertEqual(c.post('/api/v28/auth/login', json={'email': email, 'password': PASSWORD}).status_code, 503)
        self.sql('ALTER TABLE rate_limit_counters_hidden RENAME TO rate_limit_counters')
        self.clock.t += 6                     # the store is asked again STORE_RETRY_SECONDS after the failure
        self.assertEqual(c.post('/api/v28/auth/login', json={'email': email, 'password': PASSWORD}).status_code, 200)

    # ---- the store itself ---------------------------------------------------------------------------------------------
    def test_one_counter_is_counted_atomically_by_two_pools_at_once(self):
        from omni_prod.db import DatabasePool
        from omni_prod.rate_limits import PostgresRateLimitStore
        pools = [DatabasePool(self.url, max_size=20), DatabasePool(self.url, max_size=20)]
        stores = [PostgresRateLimitStore(p) for p in pools]
        row = ('concurrency_test', uuid.uuid4().hex * 2, 1_000_000, 1_000_120, 999_940)
        counts, barrier = [], threading.Barrier(40)

        def hit(i):
            barrier.wait(timeout=30)
            counts.append(stores[i % 2].hit([row])[(row[0], row[1])][0])
        threads = [threading.Thread(target=hit, args=(i,)) for i in range(40)]
        try:
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=60)
        finally:
            for p in pools:
                p.close()
        self.assertEqual(sorted(counts), list(range(1, 41)))       # no lost update, no double count

    def test_expired_counters_are_deleted_in_bounded_batches(self):
        from omni_prod import rate_limits as R
        old = [(f'sweep_{uuid.uuid4().hex[:6]}', uuid.uuid4().hex * 2) for _ in range(3)]
        self.sql("INSERT INTO rate_limit_counters (bucket, key_hash, window_start, hits, expires_at) "
                 "SELECT %s, md5(g::text) || md5((g + 1)::text), to_timestamp(1000 + g), 1, to_timestamp(2000 + g) "
                 "FROM generate_series(1, 1200) g", (old[0][0],))
        self.sql("INSERT INTO rate_limit_counters (bucket, key_hash, window_start, hits, expires_at) "
                 "VALUES (%s, %s, to_timestamp(5000), 1, to_timestamp(4000000000))", old[1])
        store = R.PostgresRateLimitStore(self.pool)
        self.assertEqual(store.sweep(3_500, batch=500, max_batches=2), 1000)        # the bound holds
        self.assertEqual(store.sweep(3_500, batch=500, max_batches=2), 200)
        self.assertEqual(self.sql('SELECT count(*) FROM rate_limit_counters WHERE bucket = %s', (old[0][0],))[0][0], 0)
        self.assertEqual(self.sql('SELECT count(*) FROM rate_limit_counters WHERE bucket = %s', (old[1][0],))[0][0], 1)
        # ... and a limited request sweeps by itself, at most once a minute per instance
        self.sql("INSERT INTO rate_limit_counters (bucket, key_hash, window_start, hits, expires_at) "
                 "VALUES (%s, %s, to_timestamp(5000), 1, to_timestamp(6000))", old[2])
        self.clock.t += R.SWEEP_INTERVAL_SECONDS + 1
        self.client(self.a).post('/api/v28/auth/verify-email', json={'token': uuid.uuid4().hex})
        self.assertEqual(self.sql('SELECT count(*) FROM rate_limit_counters WHERE bucket = %s', (old[2][0],))[0][0], 0)

    def test_social_sign_in_shares_the_counter_through_enforce(self):
        from starlette.requests import Request
        from omni_prod.rate_limits import OAUTH_START_PER_IP, RateLimited
        ip = self.ip()

        def request():
            return Request({'type': 'http', 'method': 'GET', 'path': '/api/v28/auth/oauth/google/start', 'headers': [],
                            'query_string': b'', 'client': (ip, 40000)})
        for i in range(20):
            (self.a, self.b)[i % 2]._rate_limiter.enforce(request(), OAUTH_START_PER_IP)
        with self.assertRaises(RateLimited) as refused:
            self.a._rate_limiter.enforce(request(), OAUTH_START_PER_IP)
        self.assertEqual(refused.exception.verdict.limit.name, 'oauth_start_ip')
        self.assertGreaterEqual(refused.exception.verdict.retry_after, 1)


class TheMigrationAndItsRollback(_Database):
    def test_047_creates_the_counters_with_their_rules_and_the_rollback_removes_them(self):
        import psycopg
        self.assertEqual(self.sql("SELECT to_regclass('rate_limit_counters') IS NOT NULL, "
                                  "to_regclass('rate_limit_counters_expiry') IS NOT NULL")[0], (True, True))
        self.assertEqual(self.sql('SELECT name FROM schema_migrations WHERE version = 47'), [('rate_limits',)])
        for bad in (('Login', 'a' * 64), ('login_ip', 'not-a-digest'), ('login_ip', 'A' * 64)):
            with self.subTest(bad=bad), self.assertRaises(psycopg.errors.CheckViolation):
                self.sql('INSERT INTO rate_limit_counters VALUES (%s, %s, now(), 1, now() + interval \'1 minute\')', bad)
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.sql("INSERT INTO rate_limit_counters VALUES ('login_ip', %s, now(), 0, now() + interval '1 minute')",
                     ('a' * 64,))
        with self.assertRaises(psycopg.errors.UniqueViolation):
            for _ in range(2):
                self.sql("INSERT INTO rate_limit_counters VALUES ('login_ip', %s, to_timestamp(60), 1, to_timestamp(180))",
                         ('b' * 64,))
        down = (ROOT / 'infra' / 'postgres' / 'rollback' / '047_rate_limits.down.sql').read_text(encoding='utf-8')
        with psycopg.connect(self.url, autocommit=True) as conn:
            conn.execute(down)
        self.assertEqual(self.sql("SELECT to_regclass('rate_limit_counters')")[0], (None,))
        self.assertEqual(self.sql('SELECT count(*) FROM schema_migrations WHERE version = 47')[0], (0,))
        self.assertEqual(self.sql('SELECT count(*) FROM schema_migrations WHERE version = 45')[0], (1,))


if __name__ == '__main__':
    logging.basicConfig()
    unittest.main()
