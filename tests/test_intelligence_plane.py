"""Wave A A1/A2: provider governance (matrix, prices, lifecycle) and routing
safety (task classes, mandatory floors, durable circuit breakers).

All provider answers here are TEST DOUBLES (scripted HTTP statuses); no
request leaves the process. Live provider states come only from the evidence
named in omni_prod/intelligence/inventory.py.
"""
import json
import os
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest import mock

from omni_prod.intelligence import governance, health as H, lifecycle, matrix, prices, states as S, task_policy
from omni_prod.intelligence.inventory import INVENTORY
from omni_prod.model_catalog import parse_model_catalog
from omni_prod.model_gateway import ModelGatewayError, ModelHTTPError
from omni_prod.model_policy import ModelUsePolicy
from omni_prod.model_router import RoutingPolicy
from omni_prod.routed_gateway import RoutedModelGateway

POLICY = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                        external_budget_usd=Decimal('0.50'), max_external_calls_per_build=40)


def _cat(*entries):
    return json.dumps([dict(name=n, provider=p, base_url=u, model=m, api_key_env='KEY', quality=q,
                            input_per_million=i, output_per_million=o) for n, p, u, m, q, i, o in entries])


class Script:
    def __init__(self, outcomes):
        self.outcomes = {k: list(v) for k, v in outcomes.items()}
        self.calls = []

    def factory(self, endpoint):
        script = self

        class G:
            last_usage = None

            def complete(self, **kw):
                script.calls.append(endpoint.model)
                out = script.outcomes[endpoint.model].pop(0)
                if out == 'ok':
                    return 'ok:' + endpoint.model
                status, msg = out
                raise ModelHTTPError(f'model request failed: HTTP {status}: {msg}', status=status)
        return G()


CAT = _cat(('cheap', 'x', 'https://x.example/v1', 'm-cheap', 70, '0.10', '0.40'),
           ('strong', 'x', 'https://x.example/v1', 'm-strong', 85, '0.75', '3.75'),
           ('weak', 'x', 'https://x.example/v1', 'm-weak', 60, '0.01', '0.01'))


def _gw(script, book=None, minimum=0):
    return RoutedModelGateway(ranked=parse_model_catalog(CAT, {'KEY': 'k'}), routing_policy=RoutingPolicy(minimum_quality=minimum),
                              policy=POLICY, gateway_factory=script.factory, transient_retries=0, sleep=lambda s: None,
                              health=book)


class PriceScheduleTests(unittest.TestCase):
    def test_schedule_is_valid_and_source_backed(self):
        self.assertEqual(prices.validate(), [])
        for r in prices.SCHEDULE:
            self.assertTrue(r.source_url.startswith('https://'), r.model)

    def test_announced_change_applies_on_its_date_and_history_is_kept(self):
        before = prices.price_at('gemini-3.8-flash', date(2026, 12, 31))
        after = prices.price_at('gemini-3.8-flash', date(2027, 1, 1))
        self.assertEqual((before.input_per_million, before.output_per_million), (Decimal('0.75'), Decimal('3.75')))
        self.assertEqual((after.input_per_million, after.output_per_million), (Decimal('1.50'), Decimal('7.50')))
        self.assertEqual(len(prices.history('gemini-3.8-flash')), 2)

    def test_missing_price_is_never_zero(self):
        self.assertIsNone(prices.price_at('gpt-5-nano'))
        with self.assertRaises(prices.PriceMissing):
            prices.require_price('gpt-5-nano')

    def test_overlap_detected(self):
        rows = prices.SCHEDULE + (prices._row('gemini', 'gemini-3.8-flash', src=prices.GOOGLE, inp='1', out='1'),)
        self.assertTrue(any('overlapping' in p for p in prices.validate(rows)))


class LifecycleTests(unittest.TestCase):
    def test_states_and_successor(self):
        self.assertEqual(lifecycle.state('gemini-3.1-flash-lite', date(2026, 10, 11)), lifecycle.DEPRECATION_ANNOUNCED)
        self.assertEqual(lifecycle.state('gemini-3.1-flash-lite', date(2027, 5, 7)), lifecycle.RETIRED)
        self.assertEqual(lifecycle.state('gemini-2.5-flash-lite'), lifecycle.RESTRICTED)
        self.assertEqual(lifecycle.state('gpt-5-nano-2025-08-07', date(2026, 12, 11)), lifecycle.RETIRED)
        self.assertIn('gemini-3.5-flash-lite', lifecycle.warning('gemini-3.1-flash-lite', date(2027, 3, 1)))

    def test_migration_is_a_plan_never_a_swap(self):
        plan = lifecycle.migration_plan('gemini-3.1-flash-lite', when=date(2026, 10, 11))
        self.assertEqual(plan['successor'], 'gemini-3.5-flash-lite')
        self.assertEqual(plan['action'], 'review')
        self.assertEqual(plan['compatibility'], 'UNASSESSED')
        self.assertTrue(lifecycle.migration_plan('gpt-5-nano-2025-08-07')['action'].startswith('blocked'))


class CatalogGovernanceTests(unittest.TestCase):
    REAL = 'https://generativelanguage.googleapis.com/v1beta/openai'

    def test_real_catalog_prices_match_schedule_today(self):
        raw = open(matrix.CATALOG, encoding='utf-8').read()
        models = parse_model_catalog(raw, {'GEMINI_API_KEY': 'k', 'OPENAI_API_KEY': 'k', 'ANTHROPIC_API_KEY': 'k'},
                                     when=date(2026, 10, 11))
        self.assertTrue(all(m.status == 'CONFIGURED' for m in models))
        self.assertTrue(all(m.price_source.startswith('schedule') for m in models))

    def test_schedule_overrides_stale_catalog_price_on_change_date(self):
        raw = _cat(('flash', 'gemini', self.REAL, 'gemini-3.8-flash', 85, '0.75', '3.75'))
        m, = parse_model_catalog(raw, {'KEY': 'k'}, when=date(2027, 1, 2))
        self.assertEqual((m.option.input_per_million, m.option.output_per_million), (Decimal('1.50'), Decimal('7.50')))
        self.assertTrue(any('replaced by schedule' in n for n in m.governance_notes))

    def test_managed_model_without_source_backed_price_fails_closed(self):
        raw = _cat(('nano', 'openai', 'https://api.openai.com/v1', 'gpt-5-nano', 70, '0.05', '0.40'))
        m, = parse_model_catalog(raw, {'KEY': 'k'})
        self.assertIsNone(m.endpoint)
        self.assertFalse(m.option.enabled)
        self.assertEqual(m.status, 'PRICE_UNVERIFIED')
        with mock.patch.dict(os.environ, {'OMNI_PRICE_GOVERNANCE': 'off'}):
            m, = parse_model_catalog(raw, {'KEY': 'k'})
            self.assertIsNotNone(m.endpoint)

    def test_retired_model_is_never_routed(self):
        raw = _cat(('old', 'gemini', self.REAL, 'gemini-3.1-flash-lite', 70, '0.25', '1.50'))
        m, = parse_model_catalog(raw, {'KEY': 'k'}, when=date(2027, 6, 1))
        self.assertEqual(m.status, 'RETIRED')
        self.assertIsNone(m.endpoint)

    def test_unmanaged_hosts_keep_their_price(self):
        g = governance.govern(model='anything', base_url='https://x.example/v1', input_per_million=Decimal('1'),
                              output_per_million=Decimal('2'))
        self.assertTrue(g.routable)
        self.assertEqual(g.output_per_million, Decimal('2'))


class ProviderMatrixTests(unittest.TestCase):
    def test_generated_files_are_current_and_valid(self):
        m = matrix.build()
        self.assertEqual(matrix.validate(m), [])
        js, md = matrix.render(m)
        self.assertEqual(open(matrix.JSON_OUT, encoding='utf-8').read(), js,
                         'PROVIDER_MATRIX.json is stale: python -m omni_prod.intelligence.matrix --write')
        self.assertEqual(open(matrix.MD_OUT, encoding='utf-8').read(), md)

    def test_required_fields_present(self):
        required = ('provider_key', 'model_key', 'provider_model_id', 'model_family', 'provider_type', 'capability_types',
                    'intended_task_types', 'execution_adapter', 'adapter_implementation_path', 'supported_modalities',
                    'supported_languages', 'context_window', 'maximum_output_tokens', 'supports_tool_calls',
                    'supports_structured_output', 'supports_streaming', 'supports_reasoning', 'supports_vision',
                    'supports_function_calling', 'credential_reference_names', 'credential_scope', 'credential_state',
                    'connection_state', 'verification_state', 'last_verified_at', 'evidence_reference',
                    'price_schedule_reference', 'deprecation_state', 'replacement_model', 'commercial_usage_constraints',
                    'security_constraints', 'known_limitations', 'fallback_eligibility', 'current_operational_status')
        for row in matrix.build()['models']:
            for f in required:
                self.assertIn(f, row, row['model_key'])

    def test_no_secret_values_in_the_matrix(self):
        text = open(matrix.JSON_OUT, encoding='utf-8').read()
        for pattern in ('sk-', 'AIza', 'r8_', 'Bearer '):
            self.assertNotIn(pattern, text)

    def test_inflated_states_are_rejected(self):
        import dataclasses
        from omni_prod.intelligence import inventory
        # gpt-6.1-sol: still no successful call in any ledger observation (luna has one since 2026-10-20)
        luna = next(e for e in INVENTORY if e.model_key == 'openai-gpt-6-1-sol')
        inflated = dataclasses.replace(luna, verification_state=S.REAL_EXECUTION_VERIFIED, health_note='')
        haiku = next(e for e in INVENTORY if e.model_key == 'anthropic-claude-haiku-5-5')
        fake_conn = dataclasses.replace(haiku, connection_state=S.CONNECTION_TESTED)
        live = dataclasses.replace(luna, verification_state=S.PRODUCTION_LIVE)
        for bad, needle in ((inflated, 'without execution evidence'), (fake_conn, 'without a recorded provider answer'),
                            (live, 'PRODUCTION_LIVE')):
            inv = tuple(bad if e.model_key == bad.model_key else e for e in INVENTORY)
            with mock.patch.object(matrix, 'INVENTORY', inv):
                self.assertTrue(any(needle in p for p in matrix.validate()), needle)

    def test_catalog_drift_is_rejected(self):
        cat = matrix.load_catalog()
        cat[0] = dict(cat[0], output_per_million='0.01')
        self.assertTrue(any('!= schedule' in p for p in matrix.validate(catalog=cat)))
        cat = matrix.load_catalog() + [dict(matrix.load_catalog()[0], name='new-route')]
        self.assertTrue(any('not in the inventory' in p for p in matrix.validate(catalog=cat)))

    def test_truthful_summary(self):
        m = matrix.build()
        verified = {r['provider_model_id'] for r in m['models'] if r['verification_state'] == S.REAL_EXECUTION_VERIFIED}
        self.assertEqual(verified, {'gemini-3.8-flash', 'gemini-3.1-flash-lite', 'gemini-3.5-flash-lite',
                                    'gpt-6-luna'})          # 6 ok calls, inspect-build 39378559811 (2026-10-20)
        self.assertNotIn(S.PRODUCTION_LIVE, json.dumps(m['summary']))
        blocked = {r['provider_model_id'] for r in m['models'] if r['availability'] == S.INSUFFICIENT_CREDIT}
        self.assertEqual(blocked, {'gpt-6.1-sol', 'claude-sonnet-5-5'})


class TaskPolicyRoutingTests(unittest.TestCase):
    def test_architecture_no_longer_goes_to_the_cheapest_model(self):
        s = Script({'m-strong': ['ok'], 'm-cheap': ['ok'], 'm-weak': ['ok']})
        self.assertEqual(_gw(s).complete(system='s', user='u', task='architecture'), 'ok:m-strong')

    def test_below_mandatory_floor_is_never_used_even_as_escalation(self):
        s = Script({'m-strong': [(500, 'down')], 'm-cheap': [(500, 'down')], 'm-weak': ['ok']})
        with self.assertRaises(ModelGatewayError):
            _gw(s).complete(system='s', user='u', task='codegen')
        self.assertNotIn('m-weak', s.calls)
        self.assertEqual(s.calls, ['m-strong', 'm-cheap'])  # escalation within the floor is explicit, recorded

    def test_unknown_task_gets_the_strict_default(self):
        self.assertEqual(task_policy.task_class('mystery').key, 'general')
        s = Script({'m-cheap': ['ok'], 'm-strong': [], 'm-weak': ['ok']})
        self.assertEqual(_gw(s).complete(system='s', user='u', task='mystery'), 'ok:m-cheap')
        self.assertNotIn('m-weak', s.calls)

    def test_conversation_uses_cheapest_eligible(self):
        s = Script({'m-cheap': ['ok'], 'm-strong': [], 'm-weak': []})
        self.assertEqual(_gw(s).complete(system='s', user='u', task='conversation'), 'ok:m-cheap')

    def test_floors_are_ordered(self):
        for t in task_policy.TASK_CLASSES.values():
            self.assertLessEqual(t.mandatory_floor, t.preferred_floor)
        self.assertEqual(task_policy.task_class('security_review').mandatory_floor, 85)


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.t


class CircuitBreakerTests(unittest.TestCase):
    def test_classification(self):
        e = lambda st, msg: ModelHTTPError(f'HTTP {st}: {msg}', status=st)
        self.assertEqual(H.classify(e(429, 'You have no credits remaining')), S.CREDIT_EXHAUSTED)
        self.assertEqual(H.classify(e(400, 'Your credit balance is too low')), S.CREDIT_EXHAUSTED)
        self.assertEqual(H.classify(e(401, 'invalid api key')), S.AUTH_INVALID)
        self.assertEqual(H.classify(e(429, 'You exceeded your current quota')), S.RATE_LIMITED)
        self.assertEqual(H.classify(e(404, 'model not found')), S.UNAVAILABLE)
        self.assertEqual(H.classify(e(503, 'high demand')), S.DEGRADED)
        self.assertEqual(H.classify(TimeoutError('timed out')), S.DEGRADED)
        self.assertIsNone(H.classify(e(400, 'bad request')))

    def test_credit_exhaustion_is_remembered_across_builds(self):
        store = H.MemoryHealthStore()   # stands in for provider_health (shared by all builds)
        s1 = Script({'m-cheap': [(429, 'You have no credits remaining')], 'm-strong': ['ok'], 'm-weak': []})
        self.assertEqual(_gw(s1, H.HealthBook(store)).complete(system='s', user='u', task='conversation'), 'ok:m-strong')
        self.assertEqual(store.get('cheap').state, S.CREDIT_EXHAUSTED)
        s2 = Script({'m-cheap': ['ok'], 'm-strong': ['ok'], 'm-weak': []})
        gw2 = _gw(s2, H.HealthBook(store))
        self.assertEqual(gw2.complete(system='s', user='u', task='conversation'), 'ok:m-strong')
        self.assertEqual(s2.calls, ['m-strong'])  # second build never asks the exhausted route again
        self.assertTrue(any('circuit open' in e.reason for e in gw2.events))

    def test_half_open_trial_then_close_on_success(self):
        clock, store = Clock(), H.MemoryHealthStore()
        book = H.HealthBook(store, clock=clock)
        book.record_failure('cheap', ModelHTTPError('HTTP 429: no credits', status=429))
        self.assertFalse(book.admit('cheap')[0])
        clock.t += H.RECHECK + timedelta(minutes=1)
        ok, why = book.admit('cheap')
        self.assertTrue(ok)
        self.assertIn('half-open', why)
        self.assertFalse(book.admit('cheap')[0])   # one trial only
        book.record_success('cheap')
        self.assertEqual(store.get('cheap').state, S.HEALTHY)
        self.assertTrue(book.admit('cheap')[0])

    def test_rate_limit_window_is_bounded(self):
        clock, store = Clock(), H.MemoryHealthStore()
        book = H.HealthBook(store, clock=clock)
        book.record_failure('r', ModelHTTPError('HTTP 429: quota', status=429, retry_after_seconds=10 ** 6))
        self.assertLessEqual(store.get('r').open_until - clock.t, H.MAX_RATE_COOLDOWN)
        self.assertFalse(book.admit('r')[0])
        clock.t = store.get('r').open_until
        self.assertTrue(book.admit('r')[0])

    def test_reset_requires_a_name_and_reopens(self):
        book = H.HealthBook()
        book.record_failure('r', ModelHTTPError('HTTP 401: invalid api key', status=401))
        self.assertFalse(book.admit('r')[0])
        with self.assertRaises(ValueError):
            book.reset('r', by=' ')
        book.reset('r', by='founder')
        self.assertTrue(book.admit('r')[0])

    def test_transient_errors_do_not_open_the_circuit(self):
        book = H.HealthBook()
        self.assertEqual(book.record_failure('r', ModelHTTPError('HTTP 503', status=503)), S.DEGRADED)
        self.assertIsNone(book.store.get('r'))

    def test_store_failure_never_blocks_routing(self):
        class Broken:
            def get(self, r): raise RuntimeError('db down')
            def put(self, row): raise RuntimeError('db down')
        book = H.HealthBook(Broken())
        self.assertTrue(book.admit('x')[0])
        book.record_failure('x', ModelHTTPError('HTTP 429: no credits', status=429))  # swallowed

    def test_state_transition_rules(self):
        S.check_transition('health', S.HEALTHY, S.CREDIT_EXHAUSTED)
        with self.assertRaises(ValueError):
            S.check_transition('health', S.CREDIT_EXHAUSTED, S.DEGRADED)
        with self.assertRaises(ValueError):
            S.check_transition('verification_state', S.UNVERIFIED, S.PRODUCTION_LIVE)


@unittest.skipUnless(os.getenv('M4D2_DATABASE_URL'), 'needs PostgreSQL (M4D2_DATABASE_URL)')
class PostgresHealthStoreTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.db import DatabasePool
        self.pool = DatabasePool(os.environ['M4D2_DATABASE_URL'])
        sql = open(os.path.join(os.path.dirname(__file__), '..', 'infra', 'postgres', '036_intelligence_plane.sql')).read()
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute(sql)
                conn.execute("DELETE FROM provider_health WHERE route LIKE 'test-%'")

    def test_durable_round_trip(self):
        book = H.HealthBook(H.PostgresHealthStore(self.pool))
        book.record_failure('test-a', ModelHTTPError('HTTP 400: Your credit balance is too low', status=400))
        again = H.HealthBook(H.PostgresHealthStore(self.pool))  # a new process
        self.assertEqual(again.state('test-a').state, S.CREDIT_EXHAUSTED)
        self.assertFalse(again.admit('test-a')[0])
        again.reset('test-a', by='test')
        self.assertTrue(H.HealthBook(H.PostgresHealthStore(self.pool)).admit('test-a')[0])


if __name__ == '__main__':
    unittest.main()
