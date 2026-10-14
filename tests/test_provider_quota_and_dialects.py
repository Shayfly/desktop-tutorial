"""Quota answers, refused-call accounting, budget-fit fallback and provider
request dialects (bld_ccd38bd0, 2026-10-08: Gemini free quota spent; ten HTTP
429 answers were kept at their worst case and stopped the build on budget)."""
import io
import json
import os
import unittest
from decimal import Decimal
from unittest import mock
from urllib import error

from omni_prod.model_catalog import CatalogModel, ModelCatalogError, parse_model_catalog
from omni_prod.model_gateway import (ModelEndpoint, ModelHTTPError, OpenAICompatibleGateway,
                                    ProviderQuotaUnavailable, provider_quota_depleted, quota_exhausted)
from omni_prod.model_policy import ModelPolicyViolation, ModelUsePolicy
from omni_prod.model_router import ModelOption, RoutingPolicy
from omni_prod.provider_usage import ProviderUsage
from omni_prod.routed_gateway import RoutedModelGateway
from omni_prod.model_gateway import ModelGatewayError

QUOTA = 'model request failed: HTTP 429: You exceeded your current quota, please check your plan and billing details'


def _model(name, quality, inp, out):
    return CatalogModel(endpoint=ModelEndpoint(name=name, base_url='https://x.invalid', model=name, api_key='k', external=True),
                        option=ModelOption('p', name, quality, 1000, Decimal(inp), Decimal(out)),
                        max_output_tokens=16384, api_key_env='K')


def _usage(model):
    return ProviderUsage(provider='p', model=model, external=True, request_id='r', request_id_source='header',
                         response_id='x', input_tokens=100, output_tokens=100, cached_tokens=0,
                         provider_reported_cost_usd=None, usage_reported=True)


class Script:
    """Per-model scripted answers: an exception instance or 'ok'."""

    def __init__(self, plan):
        self.plan = {k: list(v) for k, v in plan.items()}
        self.calls = []

    def factory(self, endpoint):
        script = self

        class _Gw:
            def __init__(self):
                self.last_usage = None
                self.last_response_model = endpoint.model

            def complete_json(self, **kw):
                script.calls.append(endpoint.name)
                queue = script.plan.setdefault(endpoint.name, [])
                step = queue.pop(0) if queue else 'ok'
                if step != 'ok':
                    raise step
                self.last_usage = _usage(endpoint.name)
                return {'ok': endpoint.name}
        return _Gw()


def _gw(script, models, budget='1'):
    return RoutedModelGateway(ranked=models, routing_policy=RoutingPolicy(minimum_quality=0, prefer_cost=True),
                              policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                    external_budget_usd=Decimal(budget), max_external_calls_per_build=40),
                              gateway_factory=script.factory, sleep=lambda s: None)


class QuotaTests(unittest.TestCase):
    def setUp(self):
        self.models = (_model('strong', 85, '0.75', '3.75'), _model('backup', 90, '2', '10'))

    def test_quota_answer_is_not_retried_and_the_next_provider_serves(self):
        s = Script({'strong': [ModelHTTPError(QUOTA, status=429)]})
        gw = _gw(s, self.models)
        self.assertEqual(gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen'), {'ok': 'backup'})
        self.assertEqual(s.calls, ['strong', 'backup'])
        # The refused call costs nothing; only the served call is counted.
        expected = (Decimal(100) * Decimal('2') + Decimal(100) * Decimal('10')) / Decimal(1_000_000)
        self.assertEqual(gw.state.external_spend_usd, expected)
        # Later calls in the same build skip the exhausted route entirely.
        gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
        self.assertEqual(s.calls, ['strong', 'backup', 'backup'])

    def test_only_explicit_quota_depletion_is_named(self):
        s = Script({'strong': [ModelHTTPError(QUOTA, status=429)],
                    'backup': [ModelHTTPError('HTTP 402: insufficient credit balance', status=402)]})
        gw = _gw(s, self.models)
        with self.assertRaises(ProviderQuotaUnavailable) as caught:
            gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
        self.assertEqual(caught.exception.providers, ('backup', 'strong'))
        self.assertEqual(gw.state.external_spend_usd, Decimal('0'))
        self.assertEqual(s.calls, ['strong', 'backup'])
        from omni_prod.worker_tasks import failure_code
        self.assertEqual(failure_code(caught.exception), 'provider_quota_exhausted')

    def test_bad_key_is_not_mislabeled_credit_exhaustion(self):
        s = Script({'strong': [ModelHTTPError('HTTP 401: invalid key', status=401)],
                    'backup': [ModelHTTPError('HTTP 503: overloaded', status=503)] * 3})
        gw = _gw(s, self.models)
        with self.assertRaises(ModelGatewayError) as caught:
            gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
        self.assertNotIsInstance(caught.exception, ProviderQuotaUnavailable)
        self.assertFalse(provider_quota_depleted(ModelHTTPError('HTTP 429: rate limit', status=429)))
        self.assertFalse(provider_quota_depleted(ModelHTTPError('HTTP 401: invalid key', status=401)))

    def test_plain_rate_limit_is_still_retried(self):
        s = Script({'strong': [ModelHTTPError('model request failed: HTTP 429: Too many requests', status=429)]})
        gw = _gw(s, self.models)
        self.assertEqual(gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen'), {'ok': 'strong'})
        self.assertEqual(s.calls, ['strong', 'strong'])
        self.assertNotIn('strong', gw.unavailable)

    def test_overload_refusals_do_not_eat_the_budget(self):
        busy = lambda: ModelHTTPError('model request failed: HTTP 503: high demand', status=503)
        s = Script({'strong': [busy(), busy(), busy()], 'backup': [busy(), busy(), busy()]})
        gw = _gw(s, self.models)
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
        self.assertEqual(gw.state.external_spend_usd, Decimal('0'))

    def test_timeouts_keep_their_reservation(self):
        s = Script({'strong': [ModelGatewayError('model request failed: timed out')]})
        gw = _gw(s, (self.models[0],))
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
        self.assertGreater(gw.state.external_spend_usd, Decimal('0'))

    def test_quota_detection(self):
        self.assertTrue(quota_exhausted(ModelHTTPError(QUOTA, status=429)))
        self.assertTrue(quota_exhausted(ModelHTTPError('HTTP 401: invalid x-api-key', status=401)))
        self.assertTrue(quota_exhausted(ModelHTTPError('HTTP 400: credit balance is too low', status=429)))
        self.assertFalse(quota_exhausted(ModelHTTPError('HTTP 429: rate limit', status=429)))
        self.assertTrue(quota_exhausted(ModelHTTPError('HTTP 400: Your credit balance is too low', status=400)))
        self.assertTrue(quota_exhausted(ModelHTTPError('HTTP 429: You have no credits remaining. Add credits ... /billing/', status=429)))
        self.assertFalse(quota_exhausted(ModelHTTPError('HTTP 400: invalid request', status=400)))
        self.assertFalse(quota_exhausted(ModelHTTPError('HTTP 503', status=503)))


class BudgetFitTests(unittest.TestCase):
    def test_a_route_that_does_not_fit_gives_way_to_a_cheaper_one(self):
        s = Script({})
        models = (_model('cheap', 70, '0.10', '0.50'), _model('dear', 90, '2', '10'))
        gw = _gw(s, models, budget='0.05')  # dear worst case: 10000 x $10/M = $0.10
        self.assertEqual(gw.complete_json(system='s', user='u', max_tokens=10000, task='codegen'), {'ok': 'cheap'})
        self.assertEqual(s.calls, ['cheap'])

    def test_nothing_fits_is_a_budget_stop(self):
        s = Script({})
        gw = _gw(s, (_model('dear', 90, '2', '10'),), budget='0.01')
        with self.assertRaisesRegex(ModelPolicyViolation, 'budget exceeded'):
            gw.complete_json(system='s', user='u', max_tokens=10000, task='codegen')
        self.assertEqual(s.calls, [])

    def test_zero_cost_policy_still_stops_immediately(self):
        s = Script({})
        gw = RoutedModelGateway(ranked=(_model('a', 90, '1', '1'), _model('b', 90, '1', '1')),
                                policy=ModelUsePolicy(zero_cost_mode=True), gateway_factory=s.factory)
        with self.assertRaisesRegex(ModelPolicyViolation, 'blocked by policy'):
            gw.complete_json(system='s', user='u', max_tokens=100)
        self.assertEqual(s.calls, [])


class _Resp(io.BytesIO):
    def __init__(self, payload, headers=None):
        super().__init__(json.dumps(payload).encode())
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class DialectTests(unittest.TestCase):
    def _call(self, style, payload, extra=()):
        seen = {}

        def urlopen(req, timeout):
            seen.update(url=req.full_url, headers={k.lower(): v for k, v in req.header_items()},
                        body=json.loads(req.data.decode()))
            return _Resp(payload)
        ep = ModelEndpoint(name='m', base_url='https://api.example.com/v1', model='mod', api_key='secret',
                           external=True, api_style=style, extra_body=extra)
        gw = OpenAICompatibleGateway(ep, urlopen=urlopen)
        return gw, gw.complete(system='sys', user='hi', max_tokens=300), seen

    def test_openai_reasoning_uses_max_completion_tokens_without_temperature(self):
        payload = {'choices': [{'message': {'content': 'OK'}}], 'usage': {'prompt_tokens': 5, 'completion_tokens': 2}}
        gw, text, seen = self._call('openai_reasoning', payload, extra=(('reasoning_effort', '"low"'),))
        self.assertEqual(text, 'OK')
        self.assertTrue(seen['url'].endswith('/chat/completions'))
        self.assertEqual(seen['body']['max_completion_tokens'], 300)
        self.assertNotIn('max_tokens', seen['body'])
        self.assertNotIn('temperature', seen['body'])
        self.assertEqual(seen['body']['reasoning_effort'], 'low')
        self.assertEqual(seen['headers']['authorization'], 'Bearer secret')

    def test_classic_openai_shape_unchanged(self):
        payload = {'choices': [{'message': {'content': 'OK'}}]}
        _, _, seen = self._call('openai', payload)
        self.assertEqual(seen['body']['max_tokens'], 300)
        self.assertIn('temperature', seen['body'])

    def test_anthropic_native_messages(self):
        payload = {'id': 'msg_1', 'model': 'mod', 'stop_reason': 'end_turn',
                   'content': [{'type': 'thinking', 'thinking': 'hmm'}, {'type': 'text', 'text': 'OK'}],
                   'usage': {'input_tokens': 7, 'output_tokens': 3}}
        gw, text, seen = self._call('anthropic', payload)
        self.assertEqual(text, 'OK')
        self.assertTrue(seen['url'].endswith('/v1/messages'))
        self.assertEqual(seen['headers']['x-api-key'], 'secret')
        self.assertIn('anthropic-version', seen['headers'])
        self.assertNotIn('authorization', seen['headers'])
        self.assertEqual(seen['body']['system'], 'sys')
        self.assertEqual(seen['body']['messages'], [{'role': 'user', 'content': 'hi'}])
        self.assertNotIn('temperature', seen['body'])
        self.assertEqual((gw.last_usage.input_tokens, gw.last_usage.output_tokens), (7, 3))

    def test_anthropic_without_text_is_an_error_with_stop_reason(self):
        payload = {'content': [{'type': 'thinking', 'thinking': '...'}], 'stop_reason': 'max_tokens',
                   'usage': {'input_tokens': 7, 'output_tokens': 300}}
        with self.assertRaisesRegex(ModelGatewayError, 'max_tokens'):
            self._call('anthropic', payload)

    def test_http_error_keeps_status(self):
        def urlopen(req, timeout):
            raise error.HTTPError(req.full_url, 429, 'Too Many', {}, io.BytesIO(json.dumps({'error': {'message': 'You exceeded your current quota'}}).encode()))
        ep = ModelEndpoint(name='m', base_url='https://a.example/v1', model='x', api_key='k', external=True, api_style='anthropic')
        with self.assertRaises(ModelHTTPError) as ctx:
            OpenAICompatibleGateway(ep, urlopen=urlopen).complete(system='s', user='u')
        self.assertTrue(quota_exhausted(ctx.exception))


class CatalogTests(unittest.TestCase):
    def test_repository_catalog_parses_and_keys_decide_configuration(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'infra', 'worker-host', 'model-catalog.json')
        raw = open(path).read()
        models = parse_model_catalog(raw, {'GEMINI_API_KEY': 'g', 'ANTHROPIC_API_KEY': 'a'})
        status = {m.option.model: m.status for m in models}
        self.assertEqual(status['claude-sonnet-5-5'], 'CONFIGURED')
        self.assertEqual(status['gpt-6.1-sol'], 'NOT_CONFIGURED')
        sonnet = next(m for m in models if m.option.model == 'claude-sonnet-5-5')
        self.assertEqual(sonnet.endpoint.api_style, 'anthropic')
        sol = parse_model_catalog(raw, {'OPENAI_API_KEY': 'o'})
        sol = next(m for m in sol if m.option.model == 'gpt-6.1-sol')
        self.assertEqual(sol.endpoint.api_style, 'openai_reasoning')
        self.assertEqual(dict(sol.endpoint.extra_body), {'reasoning_effort': '"low"'})

    def test_invalid_api_and_reserved_extra_fields_are_rejected(self):
        base = {'name': 'x', 'model': 'm', 'base_url': 'https://a.example', 'api_key_env': 'KEY_X', 'quality': 50,
                'input_per_million': '1', 'output_per_million': '1'}
        with self.assertRaises(ModelCatalogError):
            parse_model_catalog(json.dumps([{**base, 'api': 'soap'}]), {})
        with self.assertRaises(ModelCatalogError):
            parse_model_catalog(json.dumps([{**base, 'extra_body': {'max_tokens': 1}}]), {})


class FailureCodeTests(unittest.TestCase):
    def test_codes(self):
        from omni_prod.worker_tasks import failure_code
        self.assertEqual(failure_code(ModelPolicyViolation('external model budget exceeded')), 'model_budget_exhausted')
        self.assertEqual(failure_code(ModelPolicyViolation('external call limit exceeded')), 'model_budget_exhausted')
        self.assertEqual(failure_code(ModelPolicyViolation('external model call blocked by policy')), 'model_policy_blocked')
        self.assertEqual(failure_code(ModelGatewayError('all model routes failed: x')), 'model_unavailable')
        self.assertEqual(failure_code(RuntimeError('boom')), 'worker_exception')


class ProbeTests(unittest.TestCase):
    def test_probe_reports_each_model_without_keys(self):
        from omni_prod.model_probe import probe
        s = Script({'bad': [ModelHTTPError('HTTP 401: invalid key', status=401)]})

        class _Gw:
            def __init__(self, endpoint):
                self.inner = s.factory(endpoint)
                self.last_usage = None
                self.last_response_model = endpoint.model

            def complete(self, **kw):
                out = self.inner.complete_json(**kw)
                self.last_usage = self.inner.last_usage
                return 'OK'
        unconfigured = CatalogModel(endpoint=None, option=ModelOption('p', 'off', 50, 1, Decimal(1), Decimal(1)),
                                    max_output_tokens=10, api_key_env='OFF_KEY')
        rows = probe([_model('good', 80, '1', '1'), _model('bad', 80, '1', '1'), unconfigured], gateway_factory=_Gw)
        self.assertEqual([r['result'][:5] for r in rows], ['ok', 'error', 'not c'])
        self.assertEqual(rows[0]['metered_cost_usd'], '0.000200')
        self.assertNotIn('k', json.dumps(rows).replace('"', ' ').split())


if __name__ == '__main__':
    unittest.main()


class FittedOutputTests(unittest.TestCase):
    """Paid build bld_e2698426 (2026-10-09): the strong model's 20k-token repair
    reservation did not fit the $0.09 left; every repair went to the weak model
    and five rounds oscillated. The strong model is now tried once with the
    largest output allowance that fits, before any weaker model."""

    def setUp(self):
        self.models = (_model('weak', 70, '0.25', '1.50'), _model('strong', 85, '0.75', '3.75'))

    def test_repair_keeps_the_strong_model_with_a_smaller_output_allowance(self):
        s = Script({})
        gw = _gw(s, self.models, budget='0.06')   # 20k x 3.75/M = 0.075 does not fit; 15k does
        out = gw.complete_json(system='s', user='u' * 2000, max_tokens=20000, task='repair')
        self.assertEqual(out, {'ok': 'strong'})
        self.assertEqual(s.calls, ['strong'])
        self.assertLessEqual(gw.state.external_spend_usd, Decimal('0.06'))

    def test_too_little_budget_for_a_useful_answer_still_falls_back(self):
        s = Script({})
        gw = _gw(s, self.models, budget='0.02')   # strong: < 6000 output tokens fit; weak at 10k does
        self.assertEqual(gw.complete_json(system='s', user='u', max_tokens=10000, task='repair'), {'ok': 'weak'})

    def test_tasks_without_a_floor_are_not_stretched(self):
        s = Script({})
        gw = _gw(s, self.models, budget='0.06')
        self.assertEqual(gw.complete_json(system='s', user='u', max_tokens=20000, task='architecture'), {'ok': 'weak'})


class WriteAheadTests(unittest.TestCase):
    def test_attempt_is_recorded_and_flushed_before_the_provider_is_called(self):
        s = Script({})
        gw = _gw(s, (_model('strong', 85, '0.75', '3.75'),), budget='1')
        seen = []
        gw.on_attempt_start = lambda: seen.append([(r.outcome, len(s.calls)) for r in gw.recorder.records])
        gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
        self.assertEqual(seen, [[('unknown', 0)]])                 # in the ledger before any provider call
        self.assertEqual([r.outcome for r in gw.recorder.records], ['ok'])   # completed in place, not duplicated
