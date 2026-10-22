"""T5, Matt HOLD on #107 (T5_CONFIGURED_ROUTES_BYPASS_QUALITY_FLOOR).

Before: RoutedModelGateway._route() prepended the local primary and appended every configured fallback with
option=None, outside ranked_routes()/eligible(), and _attempt() checks money only. So a below-floor or
unknown-quality configured route could write the product:
  P1 configured fallback after the qualified catalog failed;
  P2 configured fallback when the catalog is empty or fully filtered;
  P3 the local primary, which runs BEFORE the qualified catalog;
  P4 ModelRuntimeConfig.from_env() creates a default local primary (127.0.0.1:8001, 'local-coder', no quality)
     whenever the catalog is empty.
Now the task's mandatory floor (and deny list) is applied to every route before dispatch; a configured route takes
its quality from the routable catalog entry of the same model, else from an explicitly declared quality; with
neither it is unknown and is never contacted, for any task (every task's mandatory floor is >= 70).
"""
from __future__ import annotations

import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from omni_prod.model_catalog import CatalogModel
from omni_prod.model_gateway import ModelEndpoint, ModelGatewayError
from omni_prod.model_policy import ModelUsePolicy, ModelUseState
from omni_prod.model_router import ModelOption
from omni_prod.model_runtime_config import ModelRuntimeConfig
from omni_prod.routed_gateway import ProviderRoute, RoutedModelGateway

CALL = {'system': 's', 'user': 'u', 'max_tokens': 1000}


def endpoint(name, model, external=True):
    return ModelEndpoint(name, 'https://example.invalid/v1', model, api_key='fixture-only' if external else None,
                         external=external)


def catalog(name, model, quality):
    return CatalogModel(option=ModelOption('fixture', model, quality, 100, Decimal('0.10'), Decimal('0.40')),
                        endpoint=endpoint(name, model), max_output_tokens=8000, api_key_env='FIXTURE_KEY')


class Provider:
    """Records every endpoint contacted; names in `failing` raise like a provider outage."""
    def __init__(self, contacted, failing):
        self.contacted, self.failing = contacted, failing

    def __call__(self, ep):
        outer = self

        class _GW:
            last_usage = None

            def complete_json(self, **kw):
                outer.contacted.append(ep.name)
                if ep.name in outer.failing:
                    raise RuntimeError('provider down')
                return {'ok': ep.name}

            complete = complete_json
        return _GW()


def gateway(*, ranked=(), primary=None, fallback=(), failing=()):
    contacted = []
    gw = RoutedModelGateway(ranked=ranked, primary=primary, fallback=tuple(fallback),
                            policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                  external_budget_usd=Decimal('10'), max_external_calls_per_build=20),
                            state=ModelUseState(), gateway_factory=Provider(contacted, set(failing)),
                            transient_retries=0)
    return gw, contacted


QUALIFIED = catalog('cat-strong', 'strong-90', 90)
WEAK = catalog('cat-weak', 'weak-70', 70)


class BelowFloorConfiguredRoutesAreNeverContacted(unittest.TestCase):
    def test_p1_fallback_naming_a_quality_70_catalog_model_after_the_qualified_one_fails(self):
        # Matt's repro: a qualified ranked codegen model fails; the configured fallback names a quality-70 model.
        gw, contacted = gateway(ranked=(QUALIFIED, WEAK), failing={'cat-strong'},
                                fallback=[ProviderRoute(endpoint('cfg-weak', 'weak-70'), Decimal('0.05'))])
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(task='codegen', **CALL)
        self.assertEqual(contacted, ['cat-strong'])
        self.assertTrue(any('not contacted' in e.error and e.provider == 'cfg-weak' for e in gw.events))

    def test_p2_empty_catalog_and_unknown_quality_fallback(self):
        gw, contacted = gateway(fallback=[ProviderRoute(endpoint('cfg-unknown', 'mystery-model'), Decimal('0.05'))])
        for task in ('codegen', 'repair', 'general'):
            with self.subTest(task=task), self.assertRaises(ModelGatewayError) as ctx:
                gw.complete_json(task=task, **CALL)
            self.assertIn('quality unknown', str(ctx.exception))
        self.assertEqual(contacted, [])

    def test_p2_fully_filtered_catalog_and_a_quality_70_fallback(self):
        gw, contacted = gateway(ranked=(WEAK,), fallback=[ProviderRoute(endpoint('cfg-weak', 'weak-70'), Decimal('0.05'))])
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(task='codegen', **CALL)
        self.assertEqual(contacted, [])

    def test_p3_unknown_local_primary_never_runs_before_the_qualified_catalog(self):
        gw, contacted = gateway(ranked=(QUALIFIED,), primary=ProviderRoute(endpoint('omni-local', 'local-coder', False)))
        self.assertEqual(gw.complete_json(task='codegen', **CALL), {'ok': 'cat-strong'})
        self.assertEqual(contacted, ['cat-strong'])

    def test_p3_declared_below_floor_primary_is_refused_for_codegen_only(self):
        primary = ProviderRoute(endpoint('omni-local', 'local-coder', False), declared_quality=80)
        gw, contacted = gateway(ranked=(QUALIFIED,), primary=primary)
        gw.complete_json(task='codegen', **CALL)                       # 80 < codegen's mandatory 85
        self.assertEqual(contacted, ['cat-strong'])
        contacted.clear()
        gw.complete_json(task='architecture', **CALL)                  # architecture's mandatory floor is 70
        self.assertEqual(contacted, ['omni-local'])

    def test_a_denied_model_as_configured_fallback_never_writes_code(self):
        gw, contacted = gateway(fallback=[ProviderRoute(endpoint('cfg-luna', 'gpt-6-luna'), Decimal('0.05'),
                                                        declared_quality=95)])
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(task='codegen', **CALL)
        self.assertEqual(contacted, [])

    def test_p4_from_env_default_local_primary_has_no_quality(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith(('OMNI_LOCAL_MODEL', 'OMNI_MODEL_CATALOG'))}
        with patch.dict('os.environ', env, clear=True), patch('omni_prod.model_runtime_config.load_model_catalog',
                                                              return_value=()):
            cfg = ModelRuntimeConfig.from_env()
        self.assertIsNotNone(cfg.primary)                              # the default local primary still exists
        self.assertIsNone(cfg.primary_quality)                         # ... with unknown quality
        gw, contacted = gateway(primary=ProviderRoute(cfg.primary, declared_quality=cfg.primary_quality))
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(task='codegen', **CALL)
        self.assertEqual(contacted, [])


class QualifiedConfiguredRoutesStillWork(unittest.TestCase):
    def test_a_qualified_fallback_by_catalog_quality_serves_after_the_catalog_fails(self):
        strong_b = catalog('cat-strong-b', 'strong-b-92', 92)
        gw, contacted = gateway(ranked=(QUALIFIED, strong_b), failing={'cat-strong', 'cat-strong-b'},
                                fallback=[ProviderRoute(endpoint('cfg-strong', 'strong-90'), Decimal('0.05'))])
        self.assertEqual(gw.complete_json(task='codegen', **CALL), {'ok': 'cfg-strong'})
        self.assertEqual(contacted[-1], 'cfg-strong')

    def test_a_qualified_fallback_by_declared_quality_serves_with_an_empty_catalog(self):
        gw, contacted = gateway(fallback=[ProviderRoute(endpoint('cfg-declared', 'declared-88'), Decimal('0.05'),
                                                        declared_quality=88)])
        self.assertEqual(gw.complete_json(task='codegen', **CALL), {'ok': 'cfg-declared'})

    def test_a_declared_qualified_local_primary_runs_first(self):
        gw, contacted = gateway(ranked=(QUALIFIED,),
                                primary=ProviderRoute(endpoint('omni-local', 'local-coder', False), declared_quality=90))
        self.assertEqual(gw.complete_json(task='codegen', **CALL), {'ok': 'omni-local'})


class DeclaredQualityIsExplicitConfiguration(unittest.TestCase):
    def test_env_declares_local_and_fallback_quality(self):
        env = {'OMNI_LOCAL_MODEL_URL': 'http://127.0.0.1:8001/v1', 'OMNI_LOCAL_MODEL_QUALITY': '86',
               'OMNI_EXTERNAL_MODELS_JSON': '[{"name": "a", "base_url": "https://x.invalid/v1", "model": "m", '
                                            '"api_key": "fixture-only", "quality": 88}, '
                                            '{"name": "b", "base_url": "https://x.invalid/v1", "model": "n", '
                                            '"api_key": "fixture-only"}]'}
        with patch.dict('os.environ', env), patch('omni_prod.model_runtime_config.load_model_catalog', return_value=()):
            cfg = ModelRuntimeConfig.from_env()
        self.assertEqual(cfg.primary_quality, 86)
        self.assertEqual(cfg.fallback_quality, (88, None))

    def test_invalid_declared_quality_is_refused(self):
        for raw in ('abc', '101', '-1'):
            with self.subTest(raw=raw), patch.dict('os.environ', {'OMNI_LOCAL_MODEL_URL': 'http://127.0.0.1:8001/v1',
                                                                  'OMNI_LOCAL_MODEL_QUALITY': raw}), \
                    patch('omni_prod.model_runtime_config.load_model_catalog', return_value=()):
                with self.assertRaises(RuntimeError):
                    ModelRuntimeConfig.from_env()
        with self.assertRaises(ValueError):
            ProviderRoute(endpoint('x', 'y'), declared_quality=101)


class RouteNamesCannotBorrowModelQuality(unittest.TestCase):
    def record_models(self, gw):
        seen = []
        original = gw.gateway_factory
        def factory(ep):
            provider = original(ep)
            complete = provider.complete_json
            def call(**kwargs):
                seen.append(ep.model)
                return complete(**kwargs)
            provider.complete_json = provider.complete = call
            return provider
        gw.gateway_factory = factory
        return seen

    def test_primary_name_collision_does_not_contact_unknown_weak_or_denied_model(self):
        for model, quality in (('unknown-model', None), ('weak-70', None), ('gpt-6-luna', 95)):
            with self.subTest(model=model):
                gw, _ = gateway(ranked=(QUALIFIED, WEAK), primary=ProviderRoute(
                    endpoint('cat-strong', model, False), declared_quality=quality))
                seen = self.record_models(gw)
                gw.complete_json(task='codegen', **CALL)
                self.assertEqual(seen, ['strong-90'])

    def test_fallback_name_collision_does_not_contact_unknown_weak_or_denied_model(self):
        for model, quality in (('unknown-model', None), ('weak-70', None), ('gpt-6-luna', 95)):
            with self.subTest(model=model):
                gw, _ = gateway(ranked=(QUALIFIED, WEAK), failing={'cat-strong'}, fallback=[ProviderRoute(
                    endpoint('cat-strong', model), Decimal('0.05'), declared_quality=quality)])
                seen = self.record_models(gw)
                with self.assertRaises(ModelGatewayError):
                    gw.complete_json(task='codegen', **CALL)
                self.assertEqual(seen, ['strong-90'])

    def test_catalog_actual_model_cannot_bypass_the_deny_list(self):
        from dataclasses import replace
        disguised = replace(QUALIFIED, endpoint=endpoint('cat-strong', 'gpt-6-luna'))
        gw, _ = gateway(ranked=(disguised,))
        seen = self.record_models(gw)
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(task='codegen', **CALL)
        self.assertEqual(seen, [])


if __name__ == '__main__':
    unittest.main()
