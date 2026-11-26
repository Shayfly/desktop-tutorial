"""Rate limits without a database (omni_prod/rate_limits.py; the owner, 2026-11-26): the limits and their reasons, which
routes carry them, who a request is counted as, the sliding-window arithmetic, the store-failure rule, the sentences in
Hebrew, Arabic and English, and the screen that shows them (app.js's own explain(), run in node).

The same limiter on the real routes and a real PostgreSQL, two app instances at once: tests/test_rate_limits_pg.py.
"""
from __future__ import annotations

import json
import re
import shutil
import time
import unittest
from unittest import mock

from omni_prod import rate_limits as R
from omni_prod.auth import issue_token
from omni_prod.customer_words import machine_terms

SECRET = 'unit-test-secret-' + 's' * 40


class Clock:
    def __init__(self, t: float) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class FailingStore:
    kind = 'failing'

    def __init__(self) -> None:
        self.calls = 0

    def hit(self, rows):
        self.calls += 1
        raise OSError('connection refused')


def limiter(store, t=1_000_000.0):
    return R.RateLimiter(store_factory=lambda: store, secret_factory=lambda: SECRET, clock=Clock(t))


class TheLimitsAndTheirRoutes(unittest.TestCase):
    def test_each_limit_is_stated_with_its_reason(self):
        stated = {limit.name: (limit.limit, limit.window_seconds, limit.subject) for limit in R.LIMITS}
        self.assertEqual(stated, {
            'login_identifier': (10, 900, 'identifier'), 'login_ip': (50, 900, 'ip'), 'register_ip': (10, 3600, 'ip'),
            'password_reset_identifier': (5, 3600, 'identifier'), 'password_reset_ip': (20, 3600, 'ip'),
            'verification_send_account': (5, 3600, 'account'), 'verification_send_ip': (20, 3600, 'ip'),
            'one_time_token_ip': (30, 900, 'ip'), 'password_change_account': (10, 900, 'account'),
            'password_change_ip': (50, 900, 'ip'), 'oauth_start_ip': (20, 600, 'ip'), 'oauth_callback_ip': (30, 60, 'ip')})
        for limit in R.LIMITS:
            self.assertGreater(len(limit.reason), 60, limit.name)

    def test_an_unknown_subject_or_a_limit_without_a_reason_is_refused(self):
        for bad in (dict(subject='cookie'), dict(reason=' '), dict(limit=0), dict(name='Login')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                R.Limit(**{**dict(name='x', limit=1, window_seconds=1, subject='ip', reason='a reason'), **bad})

    def test_only_the_routes_that_protect_an_account_are_limited(self):
        expected = {
            ('POST', '/api/v28/auth/login'): {'login_ip', 'login_identifier'},
            ('POST', '/api/v26/auth/login'): {'login_ip', 'login_identifier'},
            ('POST', '/api/v28/auth/register'): {'register_ip', 'login_identifier'},
            ('POST', '/api/v27/auth/register'): {'register_ip'},
            ('POST', '/api/v28/auth/password-reset/request'): {'password_reset_ip', 'password_reset_identifier'},
            ('POST', '/api/v28/auth/email-verification/request'): {'verification_send_ip', 'verification_send_account'},
            ('POST', '/api/v28/auth/verify-email'): {'one_time_token_ip'},
            ('POST', '/api/v28/auth/password-reset/confirm'): {'one_time_token_ip'},
            ('POST', '/api/v28/me/password'): {'password_change_ip', 'password_change_account'},
            # the owner, 2026-11-26 10:01: no customer limit that is not money
            ('POST', '/api/v28/projects/p1/conversation'): set(), ('POST', '/api/v28/projects/p1/builds'): set(),
            ('POST', '/api/v28/projects/p1/versions/v1/modifications'): set(),
            # social sign-in presents its own refusal (enforce), never the middleware's JSON
            ('GET', '/api/v28/auth/oauth/google/start'): set(), ('GET', '/api/v28/auth/oauth/google/callback'): set(),
            ('GET', '/api/v28/auth/login'): set(), ('POST', '/api/v28/auth/login/'): set(),
        }
        for (method, path), names in expected.items():
            with self.subTest(method=method, path=path):
                self.assertEqual({limit.name for limit in R.limits_for(method, path)}, names)

    def test_every_bound_route_exists_in_the_real_app_and_no_sign_in_route_is_left_out(self):
        from omni_prod import investor_app as app_module
        real = [(m, r.path) for r in app_module.app.routes if hasattr(r, 'methods') for m in r.methods]
        concrete = [(m, re.sub(r'\{[^}]+\}', 'x1', p)) for m, p in real]
        for route in R.ROUTES:
            if route.path.pattern in R.PENDING_ROUTES:
                continue
            with self.subTest(route=route.path.pattern):
                self.assertTrue(any(m == route.method and route.path.fullmatch(p) for m, p in concrete),
                                'a limited route that the app no longer has: its limit would silently guard nothing')
        sign_in = re.compile(r'/api/v2[678]/(auth/(login|register|password-reset/\w+|verify-email|email-verification/\w+)'
                             r'|me/password)')
        for method, path in concrete:
            if method == 'POST' and sign_in.fullmatch(path):
                with self.subTest(path=path):
                    self.assertTrue(R.limits_for(method, path), f'{path} carries no limit')

    def test_the_limiter_is_the_innermost_middleware(self):
        from omni_prod import investor_app as app_module
        self.assertIs(app_module.app.user_middleware[-1].cls, R.RateLimitMiddleware)


class WhoIsAsking(unittest.TestCase):
    SPOOF = {'x-forwarded-for': '192.0.2.1', 'forwarded': 'for=192.0.2.2', 'true-client-ip': '192.0.2.3',
             'cf-connecting-ip': '192.0.2.4', 'x-client-ip': '192.0.2.5', 'x-vercel-forwarded-for': '192.0.2.6'}

    def test_off_vercel_the_socket_peer_counts_and_every_forwarding_header_is_ignored(self):
        self.assertEqual(R.client_address({**self.SPOOF, 'x-real-ip': '192.0.2.9'}, '198.51.100.7', {}), '198.51.100.7')

    def test_on_vercel_the_edge_header_counts_and_the_rest_is_ignored(self):
        env = {'VERCEL': '1'}
        self.assertEqual(R.client_address({**self.SPOOF, 'x-real-ip': '203.0.113.5'}, '10.0.0.1', env), '203.0.113.5')
        with self.assertLogs('omni_prod.rate_limits', 'ERROR'):
            self.assertEqual(R.client_address(self.SPOOF, '10.0.0.1', env), R.UNIDENTIFIED)
        with self.assertLogs('omni_prod.rate_limits', 'ERROR'):
            self.assertEqual(R.client_address({'x-real-ip': 'not an address'}, '10.0.0.1', env), R.UNIDENTIFIED)

    def test_an_ipv6_address_counts_by_its_64_and_a_mapped_ipv4_as_itself(self):
        a = R.client_address({}, '2001:db8:1:2:aaaa::1', {})
        self.assertEqual(a, '2001:db8:1:2::/64')
        self.assertEqual(R.client_address({}, '2001:db8:1:2:ffff:ffff:ffff:ffff', {}), a)
        self.assertEqual(R.client_address({}, '::ffff:203.0.113.5', {}), '203.0.113.5')

    def test_a_peer_that_is_not_an_address_off_vercel_has_no_address_limit(self):
        self.assertIsNone(R.client_address({}, 'testclient', {}))

    def test_the_e_mail_is_read_as_the_identity_service_reads_it_whatever_the_body_size(self):
        self.assertEqual(R.identifier_of(b'{"email": "  Shai@Example.COM ", "password": "x"}'), 'shai@example.com')
        padded = json.dumps({'email': 'a@b.co', 'password': 'x', 'pad': 'p' * 200_000}).encode()
        self.assertEqual(R.identifier_of(padded), 'a@b.co')            # padding does not skip the per-e-mail count
        for body in (b'', b'not json', b'[1]', b'{"email": 5}', b'{"email": "  "}', b'\xff\xfe'):
            self.assertIsNone(R.identifier_of(body), body)

    def test_the_account_is_read_from_a_signed_session_only(self):
        token = issue_token(secret=SECRET, user_id='usr_1', org_id='o', role='creator')
        self.assertEqual(R.account_of({'authorization': f'Bearer {token}'}, {}, SECRET), 'usr_1')
        self.assertEqual(R.account_of({}, {'148ai_session': token}, SECRET), 'usr_1')
        forged = issue_token(secret='another-secret-' + 'z' * 40, user_id='usr_2', org_id='o', role='creator')
        self.assertIsNone(R.account_of({'authorization': f'Bearer {forged}'}, {}, SECRET))
        self.assertIsNone(R.account_of({}, {}, SECRET))


class TheSlidingWindow(unittest.TestCase):
    def test_the_arithmetic(self):
        login = R.LOGIN_PER_IDENTIFIER                                     # 10 per 900 s
        self.assertEqual(R.refusal_seconds(login, 100, 10, 0), 0)
        self.assertEqual(R.refusal_seconds(login, 100, 11, 0), 800 + 164)  # next window, once 11 x (1 - e/900) + 1 <= 10
        self.assertEqual(R.refusal_seconds(login, 0, 1, 10), 180)          # in this window: 10 x (1 - 180/900) + 2 = 10
        self.assertEqual(R.refusal_seconds(login, 450, 5, 10), 0)          # 10 x 0.5 + 5 = 10

    def test_a_limit_trips_one_past_its_count_and_is_back_after_the_retry(self):
        lim = limiter(R.MemoryRateLimitStore())
        hits = [(R.ONE_TIME_TOKEN_PER_IP, 'ip:203.0.113.5')]
        for _ in range(30):
            self.assertTrue(lim.check(hits).allowed)
        refused = lim.check(hits)
        self.assertEqual((refused.allowed, refused.limit.name), (False, 'one_time_token_ip'))
        lim.clock.t += refused.retry_after - 30
        again = lim.check(hits)
        self.assertFalse(again.allowed)
        lim.clock.t += again.retry_after
        self.assertTrue(lim.check(hits).allowed)

    def test_the_longest_wait_of_several_limits_is_the_one_given(self):
        lim = limiter(R.MemoryRateLimitStore())
        for _ in range(10):
            lim.check([(R.LOGIN_PER_IP, 'ip:x'), (R.LOGIN_PER_IDENTIFIER, 'e:a@b.co')])
        v = lim.check([(R.LOGIN_PER_IP, 'ip:x'), (R.LOGIN_PER_IDENTIFIER, 'e:a@b.co')])
        self.assertEqual(v.limit.name, 'login_identifier')

    def test_expired_rows_are_swept_in_a_bounded_batch_once_a_minute(self):
        store = R.MemoryRateLimitStore()
        lim = limiter(store)
        for i in range(2500):
            store.hit([('b', f'k{i}', 0, 10, -5)])
        lim.check([(R.LOGIN_PER_IP, 'ip:x')])
        self.assertEqual(len(store._rows), 2500 + 1 - R.SWEEP_BATCH * R.SWEEP_MAX_BATCHES)
        lim.check([(R.LOGIN_PER_IP, 'ip:x')])                           # within the minute: no second sweep
        self.assertEqual(len(store._rows), 501)
        lim.clock.t += R.SWEEP_INTERVAL_SECONDS
        lim.check([(R.LOGIN_PER_IP, 'ip:x')])
        self.assertEqual(len(store._rows), 1)


class WhenTheStoreCannotAnswer(unittest.TestCase):
    def test_a_failure_is_raised_and_the_store_is_not_asked_again_for_five_seconds(self):
        store = FailingStore()
        lim = limiter(store)
        with self.assertRaises(R.StoreUnavailable):
            lim.check([(R.LOGIN_PER_IP, 'ip:x')])
        with self.assertRaises(R.StoreUnavailable):
            lim.check([(R.LOGIN_PER_IP, 'ip:x')])
        self.assertEqual(store.calls, 1)
        lim.clock.t += R.STORE_RETRY_SECONDS
        with self.assertRaises(R.StoreUnavailable):
            lim.check([(R.LOGIN_PER_IP, 'ip:x')])
        self.assertEqual(store.calls, 2)

    def test_memory_mode_is_not_enforced_off_vercel_and_is_an_unavailable_store_on_vercel(self):
        with self.assertLogs('omni_prod.rate_limits', 'WARNING'):
            lim = limiter(None)
            self.assertFalse(lim.check([(R.LOGIN_PER_IP, 'ip:x')], environ={}).enforced)
        with self.assertRaises(R.StoreUnavailable):
            lim.check([(R.LOGIN_PER_IP, 'ip:x')], environ={'VERCEL': '1'})
        with mock.patch.dict('os.environ', {}, clear=False):
            import os
            os.environ.pop('VERCEL', None)
            self.assertEqual(lim.health()['status'], 'NOT_ENFORCED')

    def test_a_missing_table_is_named_with_its_migration(self):
        class NoTable(R.MemoryRateLimitStore):
            kind = 'postgres'

            def table_present(self):
                return False
        with self.assertLogs('omni_prod.rate_limits', 'ERROR'):
            health = limiter(NoTable()).health()
        self.assertEqual((health['status'], health['migration']), ('MIGRATION_MISSING', '047_rate_limits'))
        exc = R.StoreUnavailable('UndefinedTable: relation "rate_limit_counters" does not exist')
        self.assertIn('047_rate_limits', R._missing_table_hint(exc))
        self.assertEqual(R._missing_table_hint(R.StoreUnavailable('OperationalError: timeout')), '')


class WhatThePersonReads(unittest.TestCase):
    LATIN = re.compile(r'[A-Za-z]')

    def test_three_languages_no_machine_words_and_no_latin_in_hebrew_or_arabic(self):
        for seconds in (1, 61, 125, 600, 3600):
            for lang, text in {**R.refusal_messages(seconds), **{f'{k}*': v for k, v in R.unavailable_messages().items()}}.items():
                with self.subTest(lang=lang, seconds=seconds):
                    self.assertEqual(machine_terms(text), [])
                    if lang[:2] in ('he', 'ar'):
                        self.assertIsNone(self.LATIN.search(text), text)
                    self.assertNotIn('{', text)

    def test_the_wait_is_said_in_whole_minutes_with_each_languages_plural(self):
        self.assertEqual([R.wait_words('he', s) for s in (30, 120, 900)], ['בעוד דקה', 'בעוד שתי דקות', 'בעוד 15 דקות'])
        self.assertEqual([R.wait_words('ar', s) for s in (30, 120, 300, 900)],
                         ['بعد دقيقة', 'بعد دقيقتين', 'بعد 5 دقائق', 'بعد 15 دقيقة'])
        self.assertEqual([R.wait_words('en', s) for s in (30, 900)], ['in a minute', 'in 15 minutes'])

    def test_the_language_follows_lang_then_accept_language_then_hebrew(self):
        self.assertEqual(R.language_of('en', 'ar'), 'en')
        self.assertEqual(R.language_of('fr', 'ar'), 'he')                 # as investor_app._lang reads ?lang=
        self.assertEqual(R.language_of(None, 'fr-FR, ar-EG;q=0.8'), 'ar')
        self.assertEqual(R.language_of(None, None), 'he')

    def test_a_reset_answer_takes_its_floor_answered_or_raised(self):
        @R.answers_no_sooner_than(0.2)
        def fast(fail=False):
            if fail:
                raise ValueError('x')
            return 'ok'
        for fail in (False, True):
            started = time.monotonic()
            try:
                fast(fail)
            except ValueError:
                pass
            self.assertGreaterEqual(time.monotonic() - started, 0.2)
        self.assertEqual(fast.__wrapped__(), 'ok')


@unittest.skipUnless(shutil.which('node'), 'node runs app.js; CI has it')
class TheScreenShowsTheSentenceInItsLanguage(unittest.TestCase):
    def test_explain_shows_the_servers_sentence_or_the_fallback(self):
        from tests.test_plain_words_failure_and_approval import run_js
        body = R.refusal_body(R.Verdict(False, 125, R.LOGIN_PER_IP), 'he')['detail']
        down = R.unavailable_body('he')['detail']
        for lang in ('he', 'en', 'ar'):
            with self.subTest(lang=lang):
                self.assertEqual(run_js(f'explain(new ApiError(429, {json.dumps(body)}))', lang=lang),
                                 body['messages'][lang])
                self.assertEqual(run_js(f'explain(new ApiError(503, {json.dumps(down)}))', lang=lang),
                                 down['messages'][lang])
                fallback = run_js('explain(new ApiError(429, "Too Many Requests"))', lang=lang)
                self.assertEqual(fallback, run_js('t("err429")', lang=lang))
                self.assertEqual(machine_terms(fallback), [])


if __name__ == '__main__':
    unittest.main()
