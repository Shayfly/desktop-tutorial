"""C32: the intake honours OMNI_ZERO_COST_MODE / OMNI_ALLOW_EXTERNAL_FALLBACK like builds do (2026-10-20).

C30 found omni_prod/intake/reservation_worker.py:47 hard-coding zero_cost_mode=False, allow_external_fallback=True:
with OMNI_ZERO_COST_MODE=1 and OMNI_ALLOW_EXTERNAL_FALLBACK=0 a build call was blocked (ModelPolicyViolation) and an
intake call was authorized. Here the REAL build_gateway and model policy decide; only the reservation store is a fake.
"""
import json
import os
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omni_prod.intake import budget as B
from omni_prod.intake import reservation_worker as RW
from omni_prod.model_policy import ModelPolicyViolation, ModelUseState, authorize_model_call

CATALOG = (Path(__file__).resolve().parents[1] / 'infra' / 'worker-host' / 'model-catalog.json').read_text(encoding='utf-8')
MODELS = ('gemini-3.1-flash-lite',)


def env(zero, allow):
    e = {'OMNI_MODEL_CATALOG_JSON': CATALOG, 'OMNI_ZERO_COST_MODE': zero, 'OMNI_ALLOW_EXTERNAL_FALLBACK': allow,
         'OMNI_EXTERNAL_BUDGET_USD': '0.50', 'OMNI_EXTERNAL_CALLS_PER_BUILD': '20'}
    for item in json.loads(CATALOG):
        e[item['api_key_env']] = 'test-placeholder-not-a-key'
    return e


class FakeReservations:
    """Records what execute_reservation does to the reservation."""
    def __init__(self, pool):
        self.calls = []

    def claim(self, rid, **kw):
        self.calls.append('claim')
        return SimpleNamespace(id=rid, quote={'allowed_models': list(MODELS), 'task': 'conversation'},
                               quoted_usd=Decimal('0.02'))

    def payload(self, rid):
        return {'system': 's', 'user': 'u', 'max_tokens': 100, 'task': 'conversation'}

    def release(self, rid, reason):
        self.calls.append(('release', reason))

    def mark_executing(self, r, **kw):
        self.calls.append('mark_executing')
        return True

    def settle(self, r, **kw):
        self.calls.append('settle')
        return SimpleNamespace(state='SETTLED', cost_state=kw.get('cost_state'), actual_usd=None, model=None)


class BuildGatewayHonoursTheSwitches(unittest.TestCase):
    def test_zero_cost_mode_refuses_the_intake_gateway(self):
        with mock.patch.dict(os.environ, env('1', '0')):
            with self.assertRaises(ModelPolicyViolation):
                RW.build_gateway(Decimal('0.02'), MODELS)

    def test_allow_external_fallback_off_alone_also_refuses(self):
        with mock.patch.dict(os.environ, env('0', '0')):
            with self.assertRaises(ModelPolicyViolation):
                RW.build_gateway(Decimal('0.02'), MODELS)

    def test_spend_enabled_still_works_and_is_bound_to_the_quote(self):
        with mock.patch.dict(os.environ, env('0', '1')):
            gw = RW.build_gateway(Decimal('0.02'), MODELS)
        self.assertEqual((gw.policy.external_budget_usd, gw.policy.max_external_calls_per_build), (Decimal('0.02'), 1))
        authorize_model_call(endpoint=gw.ranked[0].endpoint, policy=gw.policy, state=ModelUseState(),
                             estimated_cost_usd=Decimal('0.001'))        # does not raise

    def test_build_and_intake_now_agree_under_every_switch_setting(self):
        from omni_prod.model_runtime_config import ModelRuntimeConfig
        for zero, allow in (('1', '0'), ('0', '0'), ('1', '1'), ('0', '1')):
            with mock.patch.dict(os.environ, env(zero, allow)):
                try:
                    build = ModelRuntimeConfig.from_env().policy
                    build_ok = not (build.zero_cost_mode or not build.allow_external_fallback)
                except ValueError:                     # zero_cost with allow=1: the build policy itself is refused
                    build_ok = False
                try:
                    RW.build_gateway(Decimal('0.02'), MODELS)
                    intake_ok = True
                except (ModelPolicyViolation, ValueError):
                    intake_ok = False
            self.assertEqual(intake_ok, build_ok, (zero, allow))


class ExecuteReservationReleasesBeforeAnyContact(unittest.TestCase):
    def test_kill_switch_releases_with_the_reason_and_never_executes(self):
        fake = {}

        def factory(pool):
            fake['svc'] = FakeReservations(pool)
            return fake['svc']
        with mock.patch.dict(os.environ, env('1', '0')), mock.patch.object(B, 'ReservationService', factory):
            out = RW.execute_reservation(object(), 'res_1', worker_id='w')
        self.assertEqual(out, {'ok': False, 'error': 'external model spend disabled', 'state': B.RELEASED})
        calls = fake['svc'].calls
        self.assertEqual(calls[0], 'claim')
        self.assertEqual(calls[1][0], 'release')
        self.assertIn('OMNI_ZERO_COST_MODE', calls[1][1])
        self.assertNotIn('mark_executing', calls)            # released before execution: no provider contact
        self.assertNotIn('settle', calls)


if __name__ == '__main__':
    unittest.main()


class ReplicateImageTestHonoursTheSwitches(unittest.TestCase):
    """C32 scope: the Replicate image test (investor_app.py v28_replicate_image_test_start) spends money outside the
    build path and honoured no switch."""

    def service(self, env_extra, calls):
        from omni_prod.providers.image_provider import MemorySubmissionJournal
        from omni_prod.providers.replicate_image_test import ReplicateImageTest

        def transport(req, timeout=None):
            calls.append(req.full_url)
            raise AssertionError('the provider must not be contacted')
        return ReplicateImageTest(env={'REPLICATE_API_TOKEN': 'test-only', **env_extra},
                                  journal=MemorySubmissionJournal(), store=None, urlopen=transport)

    def test_switch_off_refuses_before_any_request(self):
        for extra in ({}, {'OMNI_ZERO_COST_MODE': '1', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1'},
                      {'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '0'}):
            calls = []
            with self.assertRaises(ModelPolicyViolation):
                self.service(extra, calls).start('acct', confirmed=True)
            self.assertEqual(calls, [], extra)

    def test_switch_on_reaches_the_provider(self):
        calls = []
        with self.assertRaises(Exception) as cm:                 # the stub transport refuses, after being contacted
            self.service({'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1'}, calls).start('acct', confirmed=True)
        self.assertNotIsInstance(cm.exception, ModelPolicyViolation)
        self.assertEqual(len(calls), 1)
