import json
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from types import SimpleNamespace

from omni_prod.provider_contracts import ProviderQuote
from omni_prod.provider_pricing import (
    BuildEconomicsQuote,
    aggregate_build_quote,
    contribution_evidence,
    enforce_margin_floor,
)
from omni_prod.subscription_store import PostgresSubscriptionService
from omni_prod.pricing import PLAN_CATALOG, PlanCode
from omni_prod import investor_app, worker_tasks
from omni_prod.job_repository import PostgresBuildRepository


class QuoteAggregationTests(unittest.TestCase):
    def q(self, provider, capability, estimate, maximum, version='v1'):
        return ProviderQuote(provider, capability, Decimal(estimate), Decimal(maximum), version, 'unit', Decimal('1'))

    def test_multi_provider_max_aggregation_includes_infra_and_retry(self):
        quote = aggregate_build_quote(
            provider_quotes=(
                self.q('llm-a', 'software.code.generate', '0.20', '0.40'),
                self.q('image-b', 'media.image.generate', '0.08', '0.12'),
            ),
            infrastructure_estimated_usd=Decimal('0.10'),
            infrastructure_maximum_usd=Decimal('0.25'),
            retry_reserve_usd=Decimal('0.15'),
            revenue_usd=Decimal('2.00'),
            minimum_margin=Decimal('0.40'),
        )
        self.assertEqual(quote.provider_estimated_usd, Decimal('0.28'))
        self.assertEqual(quote.provider_maximum_usd, Decimal('0.52'))
        self.assertEqual(quote.total_estimated_variable_usd, Decimal('0.38'))
        self.assertEqual(quote.total_authorized_variable_usd, Decimal('0.92'))
        self.assertEqual(quote.retry_reserve_usd, Decimal('0.15'))
        self.assertTrue(quote.margin_floor_passed)
        self.assertEqual(quote.pricing_versions, ('v1',))

    def test_retry_cost_can_flip_margin_gate(self):
        q = self.q('p', 'c', '0.20', '0.50')
        without_retry = aggregate_build_quote(
            provider_quotes=(q,), revenue_usd=Decimal('1.00'), minimum_margin=Decimal('0.40')
        )
        with_retry = aggregate_build_quote(
            provider_quotes=(q,), retry_reserve_usd=Decimal('0.20'),
            revenue_usd=Decimal('1.00'), minimum_margin=Decimal('0.40')
        )
        self.assertTrue(without_retry.margin_floor_passed)
        self.assertFalse(with_retry.margin_floor_passed)
        with self.assertRaises(PermissionError):
            enforce_margin_floor(with_retry)

    def test_unknown_revenue_cannot_claim_margin_pass(self):
        quote = aggregate_build_quote(provider_quotes=(self.q('p','c','0.1','0.2'),))
        self.assertIsNone(quote.conservative_margin)
        self.assertIsNone(quote.margin_floor_passed)
        with self.assertRaisesRegex(PermissionError, 'revenue basis'):
            enforce_margin_floor(quote)


class ScriptedCursor:
    def __init__(self, rows, rowcounts=None):
        self.rows=list(rows)
        self.rowcounts=list(rowcounts or [])
        self.calls=[]
        self.rowcount=1
    def execute(self, sql, params=None):
        self.calls.append((' '.join(sql.split()), params))
        if self.rowcounts:
            self.rowcount=self.rowcounts.pop(0)
        else:
            self.rowcount=1
    def fetchone(self):
        return self.rows.pop(0) if self.rows else None
    def __enter__(self): return self
    def __exit__(self, *args): return False


class ReservationTests(unittest.TestCase):
    def service(self):
        return PostgresSubscriptionService(pool=None)

    def test_reservation_shortfall_denies_without_insert(self):
        # BASIC cap defaults to $2.50; already reserved/spent $2.30.
        cur=ScriptedCursor([('basic', self.service()._cycle_now(), 0, Decimal('2.30'))])
        d=self.service().reserve(
            cur, build_id='b1', user_id='u1', project_id='p1', cost_class='standard', credits=1,
            estimated_provider_cost_usd=Decimal('0.30'),
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, 'paid-provider budget exhausted')
        self.assertFalse(any('INSERT INTO credit_reservations' in sql for sql,_ in cur.calls))

    def test_reservation_takes_user_budget_row_lock_before_deciding(self):
        cur=ScriptedCursor([('basic', self.service()._cycle_now(), 0, Decimal('0'))], rowcounts=[1,1])
        d=self.service().reserve(
            cur, build_id='b1', user_id='u1', project_id='p1', cost_class='standard', credits=1,
            estimated_provider_cost_usd=Decimal('0.30'),
        )
        self.assertTrue(d.allowed)
        self.assertIn('FOR UPDATE', cur.calls[0][0])
        insert_index=next(i for i,(sql,_) in enumerate(cur.calls) if 'INSERT INTO credit_reservations' in sql)
        self.assertLess(0, insert_index)


class SettlementEvidenceTests(unittest.TestCase):
    def test_unknown_actual_cost_stays_null_and_conservative_basis_is_explicit(self):
        evidence=contribution_evidence(
            revenue_usd=Decimal('2.00'), actual_provider_cost_usd=None,
            conservative_provider_cost_usd=Decimal('0.50'), infra_cost_usd=Decimal('0.25'),
        )
        self.assertEqual(evidence['provider_cost_truth'], 'CONSERVATIVE')
        self.assertEqual(evidence['contribution_usd'], Decimal('1.25'))


class AsyncBuildAuthorizationTests(unittest.TestCase):
    def test_runtime_authorization_reserves_full_external_model_budget(self):
        env={
            'OMNI_ZERO_COST_MODE':'0', 'OMNI_ALLOW_EXTERNAL_FALLBACK':'1',
            'OMNI_EXTERNAL_BUDGET_USD':'0.30', 'OMNI_EXTERNAL_CALLS_PER_BUILD':'3',
            'OMNI_BUILD_INFRA_ESTIMATED_USD':'0.05', 'OMNI_BUILD_INFRA_MAX_USD':'0.10',
            'OMNI_MIN_BUILD_VARIABLE_MARGIN':'0.20',
        }
        with patch.dict('os.environ', env, clear=False):
            quote=investor_app._m5_build_economics_quote(PLAN_CATALOG[PlanCode.BASIC], credits=60)
        self.assertEqual(quote.provider_maximum_usd, Decimal('0.30'))
        self.assertEqual(quote.total_authorized_variable_usd, Decimal('0.40'))
        self.assertTrue(quote.margin_floor_passed)

    def test_runtime_authorization_denies_below_margin_floor(self):
        env={
            'OMNI_ZERO_COST_MODE':'0', 'OMNI_ALLOW_EXTERNAL_FALLBACK':'1',
            'OMNI_EXTERNAL_BUDGET_USD':'0.70', 'OMNI_EXTERNAL_CALLS_PER_BUILD':'3',
            'OMNI_BUILD_INFRA_ESTIMATED_USD':'0.05', 'OMNI_BUILD_INFRA_MAX_USD':'0.10',
            'OMNI_MIN_BUILD_VARIABLE_MARGIN':'0.20',
        }
        with patch.dict('os.environ', env, clear=False):
            with self.assertRaises(PermissionError):
                investor_app._m5_build_economics_quote(PLAN_CATALOG[PlanCode.BASIC], credits=60)


class BuildRepositoryEconomicsTests(unittest.TestCase):
    def test_get_request_loads_durable_authorization_and_quote_evidence(self):
        quote={'total_authorized_variable_usd':'0.40','provider_maximum_usd':'0.30'}
        row=('u1','p1','prompt',['US'],None,None,[], 'pub1', Decimal('0.30'), {'economics_quote': quote})
        cur=ScriptedCursor([row])
        repo=PostgresBuildRepository(Pool(cur))
        out=repo.get_request('b1')
        self.assertEqual(out['authorized_provider_cost_usd'], Decimal('0.30'))
        self.assertEqual(out['economics_quote'], quote)
        self.assertIn('JOIN credit_reservations', cur.calls[0][0])
        self.assertIn('JOIN build_jobs', cur.calls[0][0])

    def test_create_job_persists_initial_economics_evidence(self):
        cur=ScriptedCursor([])
        repo=PostgresBuildRepository(None)
        repo.create_with_cursor(
            cur, build_id='b1', project_id='p1', version_id='pending',
            estimated_provider_cost_usd=Decimal('0.40'),
            evidence_json={'economics_quote': {'cost_truth':'CONSERVATIVE_MAXIMUM'}},
        )
        sql,params=cur.calls[-1]
        self.assertIn('evidence_json', sql)
        self.assertIn('estimated_provider_cost_usd', sql)
        self.assertEqual(params[-1], Decimal('0.40'))


class WorkerSettlementTruthTests(unittest.TestCase):
    @staticmethod
    def gateway(spend='0', calls=0):
        return SimpleNamespace(state=SimpleNamespace(external_spend_usd=Decimal(spend), external_calls=calls))

    def test_known_capability_actual_is_settled_as_actual_when_model_has_no_external_calls(self):
        subs=MagicMock()
        subs.settle.return_value={'actual_provider_cost_usd':Decimal('0.12'),'provider_cost_truth':'ACTUAL'}
        action,evidence,actual=worker_tasks.resolve_m5_billing(
            subs, build_id='b1', ready=True, gateway=self.gateway(),
            capability_evidence={'usage':[{'actual_cost_usd':Decimal('0.12')}]},
            economics_quote={'revenue_usd':'1.00','infrastructure_maximum_usd':'0'},
        )
        self.assertEqual(action,'settled')
        self.assertEqual(actual,Decimal('0.12'))
        subs.settle.assert_called_once_with(
            build_id='b1', actual_provider_cost_usd=Decimal('0.12'),
            revenue_usd=Decimal('1.00'), infra_cost_usd=Decimal('0'),
        )
        self.assertEqual(evidence['provider_cost_truth'],'ACTUAL')

    def test_estimate_ledger_is_never_promoted_to_actual(self):
        subs=MagicMock()
        subs.settle.return_value={'actual_provider_cost_usd':None,'provider_cost_truth':'CONSERVATIVE_RESERVATION'}
        action,evidence,actual=worker_tasks.resolve_m5_billing(
            subs, build_id='b1', ready=False, gateway=self.gateway('0.25',1),
            capability_evidence=None,
            economics_quote={'revenue_usd':'1.00','infrastructure_maximum_usd':'0'},
        )
        self.assertEqual(action,'settled')
        self.assertIsNone(actual)
        subs.settle.assert_called_once_with(
            build_id='b1', actual_provider_cost_usd=None, revenue_usd=Decimal('1.00'),
            infra_cost_usd=Decimal('0'),
        )

    def test_failed_zero_spend_build_releases_reservation(self):
        subs=MagicMock()
        action,evidence,actual=worker_tasks.resolve_m5_billing(
            subs, build_id='b1', ready=False, gateway=self.gateway(),
            capability_evidence={'usage':[]}, economics_quote={},
        )
        self.assertEqual(action,'released')
        self.assertEqual(evidence,{'action':'released'})
        self.assertIsNone(actual)
        subs.release.assert_called_once_with(build_id='b1')


class Ctx:
    def __init__(self, value): self.value=value
    def __enter__(self): return self.value
    def __exit__(self, *args): return False

class Conn:
    def __init__(self, cur): self.cur=cur
    def transaction(self): return Ctx(self)
    def cursor(self): return self.cur

class Pool:
    def __init__(self, cur): self.cur=cur
    def connection(self): return Ctx(Conn(self.cur))


class SettlementServiceTests(unittest.TestCase):
    def test_settlement_returns_truthful_conservative_economics_when_actual_unknown(self):
        cur=ScriptedCursor([('u1', 'RESERVED', Decimal('0.50'), 'customer_plan')])
        service=PostgresSubscriptionService(pool=Pool(cur))
        result=service.settle(
            build_id='b1', actual_provider_cost_usd=None, revenue_usd=Decimal('2.00'),
            infra_cost_usd=Decimal('0.25'),
        )
        self.assertIsNone(result['actual_provider_cost_usd'])
        self.assertEqual(result['settled_provider_cost_usd'], Decimal('0.50'))
        self.assertEqual(result['provider_cost_truth'], 'CONSERVATIVE_RESERVATION')
        self.assertEqual(result['gross_contribution_usd'], Decimal('1.25'))
        update=next(call for call in cur.calls if "UPDATE credit_reservations SET status='SETTLED'" in call[0])
        self.assertIsNone(update[1][0])

    def test_settlement_actual_cost_uses_actual_truth(self):
        cur=ScriptedCursor([('u1', 'RESERVED', Decimal('0.50'), 'customer_plan')])
        service=PostgresSubscriptionService(pool=Pool(cur))
        result=service.settle(
            build_id='b1', actual_provider_cost_usd=Decimal('0.40'), revenue_usd=Decimal('2.00'),
            infra_cost_usd=Decimal('0.25'),
        )
        self.assertEqual(result['provider_cost_truth'], 'ACTUAL')
        self.assertEqual(result['gross_contribution_usd'], Decimal('1.35'))


class DurableBuildRouteReservationTests(unittest.TestCase):
    """M5 remediation: the canonical build route reserves the FULL conservative
    total (LLM + capabilities + generated-app infra + retry) once, before enqueue."""

    def _run(self, *, reserve_allowed=True, cost_inputs_exc=None, existing_build=None):
        from omni_prod.build_cost_plan import BuildCostInputs, CostQuoteUnknown
        from omni_prod.build_contract import BuildContractStatus

        contract = SimpleNamespace(id='bc_1', prompt='Build a CRM', contract_fingerprint='sha256:x',
                                   status=BuildContractStatus.READY, verify_fingerprint=lambda: True)
        image = ProviderQuote('image-predictions', 'media.image.generate', Decimal('0.003'), Decimal('0.01'),
                              'operator-config:p', 'image', Decimal('1'))
        inputs = BuildCostInputs((('cap-img', 'media.image.generate', image),), (),
                                 (('database', Decimal('0.02'), Decimal('0.05'), 'test'),))
        reserve = MagicMock(return_value=SimpleNamespace(allowed=reserve_allowed, reason='paid-provider budget exhausted', credits=60))
        v28 = MagicMock()
        v28.resolve_project_key.return_value = (SimpleNamespace(id='usr_1'), 'tenant_key')
        v28.subscriptions.plan_for.return_value = PLAN_CATALOG[PlanCode.BASIC]
        v28.subscriptions.reserve = reserve
        v28._project_brand_visible = {}; v28._project_white_label = {}; v28._rights_evidence = {}
        jobs = MagicMock()
        jobs.claim_contract_build.return_value = existing_build
        cursor = MagicMock(); cursor.__enter__ = lambda s: s; cursor.__exit__ = lambda *a: False
        conn = MagicMock(); conn.__enter__ = lambda s: s; conn.__exit__ = lambda *a: False
        conn.cursor.return_value = cursor
        conn.transaction.return_value = MagicMock(__enter__=lambda s: s, __exit__=lambda *a: False)
        pool = MagicMock(); pool.connection.return_value = conn
        enqueue = MagicMock()
        env = {'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1', 'OMNI_EXTERNAL_BUDGET_USD': '0.30',
               'OMNI_EXTERNAL_CALLS_PER_BUILD': '3', 'OMNI_BUILD_INFRA_ESTIMATED_USD': '0',
               'OMNI_BUILD_INFRA_MAX_USD': '0', 'OMNI_BUILD_RETRY_RESERVE_USD': '0.05',
               'OMNI_MIN_BUILD_VARIABLE_MARGIN': '0.20'}
        cost = MagicMock(side_effect=cost_inputs_exc) if cost_inputs_exc else MagicMock(return_value=inputs)
        with patch.dict('os.environ', env, clear=False), \
             patch.object(investor_app, '_require_durable_backend'), \
             patch.object(investor_app, '_v28_bearer', return_value='tok'), \
             patch.object(investor_app, '_v28', v28), \
             patch.object(investor_app, '_v28_pool', pool), \
             patch.object(investor_app, '_m5_resolve_build_contract', return_value=contract), \
             patch.object(investor_app, '_m5_cost_inputs', cost), \
             patch.object(investor_app, 'PostgresBuildContractRepository'), \
             patch.object(investor_app, 'PostgresBuildRepository', return_value=jobs), \
             patch.object(investor_app, 'enqueue_build', enqueue):
            req = investor_app.V27BuildRequest(prompt='Build a CRM', build_contract_id='bc_1')
            try:
                return investor_app.v28_build_async('prj_1', req, MagicMock()), reserve, enqueue, jobs, None
            except investor_app.HTTPException as exc:
                return None, reserve, enqueue, jobs, exc

    def test_reservation_is_the_full_conservative_total(self):
        response, reserve, enqueue, jobs, exc = self._run()
        self.assertIsNone(exc)
        # 0.30 LLM + 0.01 image + 0.05 generated-app infra + 0.05 retry
        self.assertEqual(reserve.call_args.kwargs['estimated_provider_cost_usd'], Decimal('0.41'))
        enqueue.assert_called_once()
        evidence = jobs.create_with_cursor.call_args.kwargs['evidence_json']['economics_quote']
        self.assertEqual(evidence['components']['capability_authorization_usd'], '0.01')
        self.assertEqual(evidence['total_authorized_variable_usd'], '0.41')

    def test_denied_total_reservation_enqueues_nothing(self):
        _, reserve, enqueue, jobs, exc = self._run(reserve_allowed=False)
        self.assertEqual(exc.status_code, 402)
        reserve.assert_called_once()
        enqueue.assert_not_called()
        jobs.create_outbox.assert_not_called()

    def test_second_approval_of_the_same_plan_returns_the_existing_build(self):
        # Directive 2026-10-09 §5: a double click does not create two builds.
        response, reserve, enqueue, jobs, exc = self._run(existing_build=('bld_first', 'running'))
        self.assertIsNone(exc)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.body)
        self.assertEqual((body['build_id'], body['status'], body['duplicate']), ('bld_first', 'running', True))
        reserve.assert_not_called()
        enqueue.assert_not_called()
        jobs.create_request.assert_not_called()

    def test_unknown_required_quote_blocks_before_reservation(self):
        from omni_prod.build_cost_plan import CostQuoteUnknown
        _, reserve, enqueue, _, exc = self._run(cost_inputs_exc=CostQuoteUnknown(['capability media.image.generate has no configured provider quote']))
        self.assertEqual(exc.status_code, 402)
        self.assertEqual(exc.detail['error'], 'cost_quote_unknown')
        reserve.assert_not_called()
        enqueue.assert_not_called()


if __name__ == '__main__':
    unittest.main()
