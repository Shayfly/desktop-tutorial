"""Michael 2026-11-15: vision first, then the live probe. A call carrying images is routed only to a model on
omni_prod.vision_models (evidence that it reads images); every other model is recorded as not contacted, and with no
vision route left the call fails loudly instead of being answered by a model that never saw the picture.

Real path: the worker's own model catalog file (infra/worker-host/model-catalog.json, the six routed models), parsed by
model_catalog.parse_model_catalog, behind the real RoutedModelGateway with task='review' -- the task lens 11 and the
design review use. Only the provider HTTP call is replaced (it records which endpoint was contacted)."""
from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

from omni_prod.model_catalog import parse_model_catalog
from omni_prod.model_gateway import ModelGatewayError
from omni_prod.model_policy import ModelUsePolicy, ModelUseState
from omni_prod.routed_gateway import RoutedModelGateway
from unittest import mock

from omni_prod import vision_models
from omni_prod.vision_models import VISION_MODELS

CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'infra' / 'worker-host' / 'model-catalog.json').read_text())
# Pending enrollment has no vision evidence and cannot route. This fixture
# exercises the six enabled production routes and their original live probe.
RAW = json.dumps([row for row in CATALOG if row.get('enabled', True)])
# Since the live probe (run 43657047045) every real catalog model reads images. A model without evidence -- a new one
# before its probe -- is simulated by taking the cheapest real model OFF the list for these tests (mock.patch.dict).
BLIND = min(json.loads(RAW), key=lambda m: (float(m['output_per_million']), m['model']))['model']
ENV = {item['api_key_env']: 'fixture-only' for item in json.loads(RAW)}
IMAGE = (b'\xff\xd8\xff\xe0' + b'0' * 64,)


class Provider:
    def __init__(self, contacted, failing):
        self.contacted, self.failing = contacted, failing

    def __call__(self, ep):
        outer = self

        class _GW:
            last_usage = None

            def complete_json(self, **kw):
                outer.contacted.append((ep.model, bool(kw.get('images'))))
                if ep.model in outer.failing:
                    raise RuntimeError('provider down')
                return {'ok': ep.model}
            complete = complete_json
        return _GW()


def gateway(failing=()):
    contacted = []
    gw = RoutedModelGateway(ranked=parse_model_catalog(RAW, ENV), primary=None, fallback=(),
                            policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                  external_budget_usd=Decimal('10'), max_external_calls_per_build=20),
                            state=ModelUseState(), gateway_factory=Provider(contacted, set(failing)), transient_retries=0)
    return gw, contacted


class EveryRealModelHasEvidence(unittest.TestCase):
    def test_the_six_catalog_models_are_on_the_list_with_the_probe_run(self):
        models = {m['model'] for m in json.loads(RAW)}
        self.assertEqual(models - set(VISION_MODELS), set())
        self.assertTrue(all('43657047045' in VISION_MODELS[m] for m in models))


class VisionRouteGuard(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(vision_models.VISION_MODELS)
        self.patch.start()
        del vision_models.VISION_MODELS[BLIND]                 # this model has no evidence in these tests
        self.addCleanup(self.patch.stop)

    def test_the_catalog_has_blind_and_vision_models(self):
        models = {m.endpoint.model for m in parse_model_catalog(RAW, ENV)}
        self.assertTrue(models & set(VISION_MODELS))
        self.assertIn(BLIND, models - set(VISION_MODELS))

    def test_an_image_call_goes_only_to_a_vision_model(self):
        gw, contacted = gateway()
        gw.complete_json(system='s', user='u', max_tokens=300, task='review', images=IMAGE)
        self.assertEqual(len(contacted), 1)
        self.assertIn(contacted[0][0], VISION_MODELS)
        blind = [e for e in gw.events if 'no evidence this model reads images' in (e.error or '')]
        self.assertTrue(blind)
        self.assertTrue(all(e.model not in VISION_MODELS for e in blind))

    def test_when_every_vision_model_fails_no_blind_model_is_tried(self):
        gw, contacted = gateway(failing=set(VISION_MODELS))
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(system='s', user='u', max_tokens=300, task='review', images=IMAGE)
        self.assertTrue(contacted)
        self.assertTrue(all(model in VISION_MODELS for model, _ in contacted), contacted)

    def test_no_vision_route_at_all_fails_loudly(self):
        blind_only = json.dumps([m for m in json.loads(RAW) if m['model'] not in vision_models.VISION_MODELS])
        contacted = []
        gw = RoutedModelGateway(ranked=parse_model_catalog(blind_only, ENV), primary=None, fallback=(),
                                policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                      external_budget_usd=Decimal('10'), max_external_calls_per_build=20),
                                state=ModelUseState(), gateway_factory=Provider(contacted, set()), transient_retries=0)
        with self.assertRaisesRegex(ModelGatewayError, 'no vision-capable model route'):
            gw.complete_json(system='s', user='u', max_tokens=300, task='review', images=IMAGE)
        self.assertEqual(contacted, [])

    def test_a_call_without_images_is_routed_as_before(self):
        gw, contacted = gateway(failing=set(VISION_MODELS))
        gw.complete_json(system='s', user='u', max_tokens=300, task='review')
        self.assertTrue(any(model not in VISION_MODELS for model, _ in contacted), contacted)


if __name__ == '__main__':
    unittest.main()
