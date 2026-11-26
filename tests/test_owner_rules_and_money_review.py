"""The owner's decisions of 2026-11-26 ~16:10 UTC and the money review of 00d7404.

  * "כרגע לא, רק באישור שלי": the removals apply to usr_GCWlMxENgr9vpwph only. OMNI_FOUNDER_ACCOUNT_IDS does not widen
    them (pricing.owner_account ignores it).
  * "כן. רק מדידה": the owner's conversations have no per-project or daily cap (a $50 safety bound per reservation).
  * S1: a configured fallback route without a catalog price keeps its flat per-call authorization as its cost.
  * S2: the reconciler charges a price-unknown call its stand-in instead of holding the reservation for ever.
  * S3: BOUND_NEAR is logged past 80% of a bound, and when one call jumps from under 80% to a refusal.
Real RoutedModelGateway, real resolve_m5_billing, the real reconciler verdict; only the provider answer is a double."""
from __future__ import annotations

import json
import os
import unittest
import uuid
from decimal import Decimal
from unittest import mock

OWNER = 'usr_GCWlMxENgr9vpwph'


class TheRulesAreTheOwnersOnly(unittest.TestCase):
    def test_the_founder_env_list_does_not_widen_the_new_rules(self):
        from omni_prod.pricing import founder_no_build_limit, m5_founder_account, owner_account
        with mock.patch.dict(os.environ, {'OMNI_FOUNDER_ACCOUNT_IDS': f'{OWNER},usr_partner'}):
            self.assertTrue(m5_founder_account('usr_partner'))           # the older founder rules read the list
            self.assertFalse(founder_no_build_limit('usr_partner'))      # the new ones do not
            self.assertFalse(owner_account('usr_partner'))
            self.assertTrue(founder_no_build_limit(OWNER))
        with mock.patch.dict(os.environ, {'OMNI_FOUNDER_ACCOUNT_IDS': 'usr_partner'}):
            self.assertTrue(founder_no_build_limit(OWNER))               # and removing him from it changes nothing

    def test_a_listed_partner_keeps_the_worker_budget_for_change_requests(self):
        from omni_prod.worker_tasks import bind_founder_change_request
        with mock.patch.dict(os.environ, {'OMNI_FOUNDER_ACCOUNT_IDS': f'{OWNER},usr_partner'}):
            self.assertIsNone(bind_founder_change_request(_gateway(_unpriced_catalog()), {'user_id': 'usr_partner'}))


class _Reservations:
    def __init__(self, spent):
        self.spent = Decimal(spent)

    def counted(self, scope, cur=None):
        return self.spent

    def open_held(self, scope):
        return Decimal('0')


class TheOwnersConversationIsOnlyMeasured(unittest.TestCase):
    ENV = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.05',
           'OMNI_INTAKE_DAILY_BUDGET_USD': '0.15', 'OMNI_INTAKE_CALL_BUDGET_USD': '0.01'}

    def _sup(self, spent):
        from omni_prod.conversation.supervisor import ConversationSupervisor
        return ConversationSupervisor(briefs=None, store=None, credits=10, context=lambda p: {},
                                      reservations=_Reservations(spent), enqueue=lambda rid: None)

    def test_the_owner_passes_the_caps_a_customer_hits(self):
        with mock.patch.dict(os.environ, {**self.ENV, 'OMNI_FOUNDER_ACCOUNT_IDS': f'{OWNER},usr_partner'}):
            sup = self._sup('1.00')                                       # far past both caps
            self.assertEqual(sup.intake_mode('prj_a', OWNER).mode, 'model-via-worker')
            for other in ('usr_partner', 'usr_customer'):
                m = sup.intake_mode('prj_a', other)
                self.assertEqual((m.mode, m.limit), ('deterministic', 'budget'), other)

    def test_the_owners_reservation_carries_the_safety_bound_not_the_caps(self):
        from omni_prod.intake.budget import OWNER_INTAKE_SAFETY_USD
        with mock.patch.dict(os.environ, self.ENV):
            sup = self._sup('0')
            owner = sup._interpreter('prj_a', OWNER, request_key='k1')
            other = sup._interpreter('prj_a', 'usr_customer', request_key='k2')
        self.assertEqual((owner.caps.project_usd, owner.caps.daily_usd), (OWNER_INTAKE_SAFETY_USD, OWNER_INTAKE_SAFETY_USD))
        self.assertLessEqual(other.caps.project_usd, Decimal('0.05'))
        self.assertEqual(other.caps.daily_usd, Decimal('0.15'))


def _gateway(catalog=None, fallback=(), budget='5', calls=150, factory=None):
    from omni_prod.model_policy import ModelUsePolicy
    from omni_prod.model_router import RoutingPolicy
    from omni_prod.routed_gateway import RoutedModelGateway
    return RoutedModelGateway(ranked=catalog or (), fallback=fallback, routing_policy=RoutingPolicy(minimum_quality=70),
                              policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                    external_budget_usd=Decimal(budget), max_external_calls_per_build=calls),
                              gateway_factory=factory or _Provider, sleep=lambda s: None)


class _Provider:
    def __init__(self, endpoint):
        self.endpoint, self.last_usage, self.last_response_model = endpoint, None, endpoint.model

    def _usage(self):
        from omni_prod.provider_usage import ProviderUsage
        return ProviderUsage(provider='p', model=self.endpoint.model, external=True, request_id='r_' + uuid.uuid4().hex,
                             request_id_source='header', response_id=None, input_tokens=2000, output_tokens=4000,
                             cached_tokens=None, provider_reported_cost_usd=None, usage_reported=True)

    def complete(self, **kw):
        self.last_usage = self._usage()
        return 'ok'

    complete_json = lambda self, **kw: (self.complete(), {'ok': True})[1]   # noqa: E731


class _Subs:
    def settle(self, **kw):
        self.kw = kw
        return {}

    def release_failed(self, **kw):
        self.kw = kw
        return {}


class TheFallbackRouteKeepsItsAuthorization(unittest.TestCase):
    def test_a_configured_route_without_a_catalog_price_settles_at_its_flat_authorization(self):
        # the review's probe: three calls on OMNI_EXTERNAL_MODELS_JSON at $0.25 each settle at 0.75, not 0.00
        from omni_prod import worker_tasks
        from omni_prod.model_gateway import ModelEndpoint
        from omni_prod.routed_gateway import ProviderRoute
        ep = ModelEndpoint(name='ext-fallback', base_url='https://api.openai.com/v1', model='gpt-6.1-sol', api_key='k',
                           timeout_seconds=30, external=True)
        gw = _gateway(fallback=(ProviderRoute(ep, Decimal('0.25'), declared_quality=90),), budget='1.00')
        for _ in range(3):
            gw.complete(system='s', user='u', max_tokens=4000)
        subs = _Subs()
        worker_tasks.resolve_m5_billing(subs, build_id='b1', ready=True, gateway=gw, capability_evidence=None,
                                        economics_quote={'infrastructure_maximum_usd': '0'})
        self.assertEqual(subs.kw['computed_provider_cost_usd'], Decimal('0.75'))
        self.assertEqual(worker_tasks._unpriced_calls(gw), [])


def _unpriced_catalog():
    from omni_prod.model_catalog import parse_model_catalog
    return parse_model_catalog(json.dumps([{'name': 'writer', 'provider': 'labs', 'base_url': 'https://models.test/v1',
                                            'model': 'writer-1', 'api_key_env': 'WRITER_KEY', 'quality': 92}]),
                               {'WRITER_KEY': 'k'})


class AnUnpricedCallIsChargedItsStandIn(unittest.TestCase):
    def test_a_customer_build_is_charged_the_stand_in_not_zero(self):
        from omni_prod import worker_tasks
        gw = _gateway(_unpriced_catalog())
        gw.complete(system='s', user='u', max_tokens=1000)
        stand_in = sum(r.authorized_cost_usd for r in gw.recorder.records)
        self.assertGreater(stand_in, 0)
        subs = _Subs()
        _, evidence, actual = worker_tasks.resolve_m5_billing(
            subs, build_id='b1', ready=True, gateway=gw, capability_evidence=None,
            economics_quote={'infrastructure_maximum_usd': '0', 'total_authorized_variable_usd': '5'})
        self.assertIsNone(actual)
        self.assertEqual(subs.kw['computed_provider_cost_usd'], stand_in)
        record = evidence['cost_record']
        self.assertEqual((Decimal(record['stand_in_usd']), Decimal(record['llm_known_usd'])), (stand_in, Decimal('0')))
        self.assertEqual(worker_tasks.recorded_ai_cost(evidence), 'unknown')  # no known model cost: NULL (048)

    def test_the_stand_in_is_capped_at_the_reservation(self):
        from omni_prod import worker_tasks
        gw = _gateway(_unpriced_catalog())
        gw.complete(system='s', user='u', max_tokens=1000)
        subs = _Subs()
        worker_tasks.resolve_m5_billing(subs, build_id='b1', ready=True, gateway=gw, capability_evidence=None,
                                        economics_quote={'infrastructure_maximum_usd': '0',
                                                         'total_authorized_variable_usd': '0.01'})
        self.assertEqual(subs.kw['computed_provider_cost_usd'], Decimal('0.01'))


class _Cur:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, sql, params=None):
        self.sql = sql

    def fetchall(self):
        return self.rows


class TheReconcilerDoesNotHoldAPriceUnknownCall(unittest.TestCase):
    def test_a_price_unknown_call_is_charged_its_stand_in(self):
        from omni_prod.attempt_ledger import PRICE_UNKNOWN_MARK
        from omni_prod.reservation_reconciler import verdict
        rows = [('ok', Decimal('0.10'), 'cheapest', Decimal('0.2')),
                ('ok', None, f'cheapest; {PRICE_UNKNOWN_MARK}', Decimal('0.05'))]
        action, total, reason = verdict(_Cur(rows), 'b1')
        self.assertEqual((action, total), ('release_metered', Decimal('0.15')))
        self.assertIn('stand-in', reason)

    def test_a_genuinely_unknown_call_still_holds(self):
        from omni_prod.reservation_reconciler import verdict
        self.assertEqual(verdict(_Cur([('ok', None, 'cheapest', Decimal('0.05'))]), 'b1')[0], 'hold')
        self.assertEqual(verdict(_Cur([('unknown', None, 'x', Decimal('0.05'))]), 'b1')[0], 'hold')


class BoundNear(unittest.TestCase):
    def _priced(self):
        from omni_prod.model_catalog import parse_model_catalog
        return parse_model_catalog(json.dumps([{'name': 'm', 'provider': 'p', 'base_url': 'https://models.test/v1',
                                                'model': 'm-1', 'api_key_env': 'M_KEY', 'quality': 92,
                                                'input_per_million': '1', 'output_per_million': '10'}]), {'M_KEY': 'k'})

    def test_a_build_that_crosses_80_percent_of_its_calls_is_logged(self):
        gw = _gateway(self._priced(), calls=5)
        with self.assertLogs('omni_prod.routed_gateway', level='WARNING') as logs:
            for _ in range(4):
                gw.complete(system='s', user='u', max_tokens=100)
        self.assertEqual([b['bound'] for b in gw.near_bounds], ['external_calls'])
        self.assertIn('BOUND_NEAR external_calls 4 of 5', '\n'.join(logs.output))

    def test_the_money_value_is_labelled_authorized_not_spend(self):
        gw = _gateway(self._priced(), budget='0.05')
        with self.assertLogs('omni_prod.routed_gateway', level='WARNING') as logs:
            gw.complete(system='s', user='u', max_tokens=4000)        # worst case 0.04 of 0.05 authorized
        item = next(b for b in gw.near_bounds if b['bound'] == 'external_authorized_usd')
        self.assertEqual(item['value'], 'authorized ledger, not spend')
        self.assertIn('authorized, not spend', '\n'.join(logs.output))

    def test_a_jump_from_under_80_percent_to_a_refusal_is_logged(self):
        from omni_prod.model_policy import ModelPolicyViolation
        gw = _gateway(self._priced(), budget='0.01')
        with self.assertLogs('omni_prod.routed_gateway', level='WARNING') as logs:
            with self.assertRaises(ModelPolicyViolation):
                gw.complete(system='s', user='u', max_tokens=50000)  # one call of $0.50 against $0.01: refused at once
        item = next(b for b in gw.near_bounds if b['bound'] == 'external_authorized_usd')
        self.assertIn('refused_at_the_bound', item)
        self.assertIn('refused: would reach', '\n'.join(logs.output))


if __name__ == '__main__':
    unittest.main()
