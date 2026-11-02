"""Owner accounts in production (founder 2026-11-02 19:26, option a).

The real blocker on the owner's account was `plan_cannot_authorize_cost`: 15 credits left, the build needs 45, and
INTERNAL_QA funding (where credits never block) is off in production. `OMNI_OWNER_ACCOUNT_IDS` turns that same,
existing INTERNAL_QA path on in production for exactly the listed account ids; caps stay (defaults 1.00 per build,
20.00 total); unset / unlisted -> production behaves exactly as before. subscription_store is not touched.
"""
import importlib.util
import os
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.creator_plan import build_plan_preview
from omni_prod.pricing import PLAN_CATALOG, PlanCode
from omni_prod.product_architect import ProductArchitect
from omni_prod.qa_budget import OWNER_GRANT, QABudgetDenied, QABudgetPolicy, authorize_qa_build, entitled_account
from omni_prod.subscription_store import PostgresSubscriptionService


class ScriptedCursor:                              # same as tests/test_m5_build_economics (that module imports fastapi)
    def __init__(self, rows):
        self.rows, self.calls, self.rowcount = list(rows), [], 1

    def execute(self, sql, params=None):
        self.calls.append((' '.join(sql.split()), params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Ctx:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self.value

    def __exit__(self, *args):
        return False


class _Conn:
    def __init__(self, cur):
        self.cur = cur

    def cursor(self):
        return self.cur

    def transaction(self):
        return _Ctx(None)

    def execute(self, sql, params=None):
        self.cur.execute(sql, params)
        return self.cur


class Pool:
    def __init__(self, cur):
        self.cur = cur

    def connection(self):
        return _Ctx(_Conn(self.cur))

OWNER = 'acct_owner_1'
CUSTOMER = 'acct_customer_9'
PROD = {'VERCEL_ENV': 'production', 'OMNI_ENV': 'production'}


class _Cur:
    def __init__(self, used_usd):
        self.used, self.calls = used_usd, []

    def execute(self, sql, params=None):
        self.calls.append(' '.join(sql.split()))

    def fetchone(self):
        return (self.used,)


class Policy(unittest.TestCase):
    def test_owner_list_enables_production_with_default_caps(self):
        p = QABudgetPolicy.from_env({**PROD, 'OMNI_OWNER_ACCOUNT_IDS': f' {OWNER} , other '})
        self.assertEqual((p.enabled, p.environment, p.build_max_usd, p.total_usd, p.owner_ids),
                         (True, 'production', Decimal('1.00'), Decimal('20.00'), frozenset({OWNER, 'other'})))
        caps = QABudgetPolicy.from_env({**PROD, 'OMNI_OWNER_ACCOUNT_IDS': OWNER, 'OMNI_QA_BUILD_MAX_USD': '0.75',
                                        'OMNI_QA_BUDGET_TOTAL_USD': '5'})
        self.assertEqual((caps.build_max_usd, caps.total_usd), (Decimal('0.75'), Decimal('5')))
        self.assertFalse(QABudgetPolicy.from_env({**PROD, 'OMNI_OWNER_ACCOUNT_IDS': OWNER,
                                                  'OMNI_QA_BUILD_MAX_USD': '30'}).enabled)   # per-build > total

    def test_unset_or_empty_list_is_todays_production(self):
        for env in (PROD, {**PROD, 'OMNI_OWNER_ACCOUNT_IDS': ''}, {**PROD, 'OMNI_OWNER_ACCOUNT_IDS': ' , '}):
            with self.subTest(env=env):
                p = QABudgetPolicy.from_env(env)
                self.assertFalse(p.enabled)
                self.assertEqual(p.reason, 'internal QA funding is disabled in production')

    def test_the_list_is_the_grant_and_no_database_row_is_read(self):
        p = QABudgetPolicy.from_env({**PROD, 'OMNI_OWNER_ACCOUNT_IDS': OWNER})
        self.assertTrue(entitled_account(None, p, OWNER))          # no pool needed: nothing is queried
        self.assertFalse(entitled_account(None, p, CUSTOMER))
        self.assertFalse(entitled_account(None, p, ''))

    def test_staging_still_uses_the_entitlement_table(self):
        p = QABudgetPolicy.from_env({'OMNI_ENV': 'staging', 'OMNI_QA_BUILD_MAX_USD': '0.5',
                                     'OMNI_QA_BUDGET_TOTAL_USD': '10', 'OMNI_OWNER_ACCOUNT_IDS': OWNER})
        self.assertEqual((p.environment, p.owner_ids), ('staging', frozenset()))   # the env list is production-only


def preview(*, internal_qa: bool, credits_used: int):
    """The plan view exactly as investor_app.v28 plan builds it: authorize_quote is None for INTERNAL_QA funding,
    otherwise the customer plan's authorize() (credits checked)."""
    quote = SimpleNamespace(total_authorized_variable_usd=Decimal('0.35'))
    cur = ScriptedCursor([('basic', PostgresSubscriptionService(pool=Pool(ScriptedCursor([])))._cycle_now(),
                           credits_used, Decimal('0'))])
    service = PostgresSubscriptionService(pool=Pool(cur))
    return build_plan_preview(
        architect=ProductArchitect(), repository=MemoryBuildContractRepository(), project_id='p',
        prompt='Build a simple static page for a flower shop, no login, no personal data.',
        economics=lambda: quote,
        authorize_quote=None if internal_qa else (lambda q: service.authorize(
            user_id='u', cost_class='light', credits=60, estimated_provider_cost_usd=q.total_authorized_variable_usd)),
        durable_backend=True, infrastructure_readiness={'kinds': {}}, image_readiness={'status': 'PARTIAL'})


class PlanViewAndAdmission(unittest.TestCase):
    EXHAUSTED = PLAN_CATALOG[PlanCode.AMATEUR].included_credits     # no credits left

    def funding(self, account_id, env):
        # investor_app._internal_qa_funding is exactly these two calls (checked against the real function in
        # test_the_endpoint_uses_the_same_decision, which needs fastapi and runs in CI)
        with mock.patch.dict(os.environ, env, clear=False):
            policy = QABudgetPolicy.from_env()
        return policy, entitled_account(None, policy, account_id)

    @unittest.skipUnless(importlib.util.find_spec('fastapi'), 'fastapi is not installed here (CI has it)')
    def test_the_endpoint_uses_the_same_decision(self):
        import omni_prod.investor_app as app
        for env, account, expected in (({**PROD, 'OMNI_OWNER_ACCOUNT_IDS': OWNER}, OWNER, True),
                                       ({**PROD, 'OMNI_OWNER_ACCOUNT_IDS': OWNER}, CUSTOMER, False),
                                       (PROD, OWNER, False)):
            with self.subTest(account=account, env=env), mock.patch.dict(os.environ, env, clear=False), \
                    mock.patch.object(app, '_v28_pool', None):
                self.assertEqual(app._internal_qa_funding(account)[1], expected)

    def test_listed_owner_builds_without_credits(self):
        policy, internal_qa = self.funding(OWNER, {**PROD, 'OMNI_OWNER_ACCOUNT_IDS': OWNER})
        p = preview(internal_qa=internal_qa, credits_used=self.EXHAUSTED)
        print('\n[owner]', internal_qa, p['can_build'], p['blockers'])
        self.assertTrue(internal_qa)
        self.assertTrue(p['can_build'])
        grant = authorize_qa_build(_Cur(Decimal('0')), policy, account_id=OWNER, max_cost_usd=Decimal('0.35'))
        self.assertEqual((grant['entitlement_id'], grant['funding_source'], grant['owner_mode']),
                         (OWNER_GRANT, 'internal_qa', True))

    def test_unlisted_account_is_blocked_as_before(self):
        policy, internal_qa = self.funding(CUSTOMER, {**PROD, 'OMNI_OWNER_ACCOUNT_IDS': OWNER})
        p = preview(internal_qa=internal_qa, credits_used=self.EXHAUSTED)
        print('[customer]', internal_qa, p['can_build'], [b['code'] for b in p['blockers']])
        self.assertFalse(internal_qa)
        self.assertFalse(p['can_build'])
        self.assertIn('plan_cannot_authorize_cost', [b['code'] for b in p['blockers']])
        with self.assertRaises(QABudgetDenied):                       # and admission refuses QA funding for it
            authorize_qa_build(_Cur(Decimal('0')), policy, account_id=CUSTOMER, max_cost_usd=Decimal('0.35'))

    def test_no_list_means_the_owner_is_a_customer_again(self):
        _, internal_qa = self.funding(OWNER, {**PROD, 'OMNI_OWNER_ACCOUNT_IDS': ''})
        self.assertFalse(internal_qa)

    def test_exhausted_caps_block_with_an_explicit_message(self):
        policy, _ = self.funding(OWNER, {**PROD, 'OMNI_OWNER_ACCOUNT_IDS': OWNER})
        with self.assertRaises(QABudgetDenied) as total:
            authorize_qa_build(_Cur(Decimal('19.80')), policy, account_id=OWNER, max_cost_usd=Decimal('0.35'))
        with self.assertRaises(QABudgetDenied) as one:
            authorize_qa_build(_Cur(Decimal('0')), policy, account_id=OWNER, max_cost_usd=Decimal('1.20'))
        print('[caps]', total.exception, '|', one.exception)
        self.assertEqual(str(total.exception), 'QA total budget exhausted: used 19.80 + this build 0.35 > cap 20.00')
        self.assertEqual(str(one.exception), 'QA build maximum 1.20 exceeds per-build cap 1.00')

        def economics():
            raise total.exception                                       # what the plan view does on that refusal
        p = build_plan_preview(
            architect=ProductArchitect(), repository=MemoryBuildContractRepository(), project_id='p',
            prompt='Build a simple static page for a flower shop, no login, no personal data.', economics=economics,
            authorize_quote=None, durable_backend=True, infrastructure_readiness={'kinds': {}},
            image_readiness={'status': 'PARTIAL'})
        blocker = next(b for b in p['blockers'] if b['code'] == 'qa_budget_denied')
        self.assertEqual(blocker['message'], 'QA total budget exhausted: used 19.80 + this build 0.35 > cap 20.00')
        self.assertEqual((p['can_build'], p['execution_readiness']), (False, 'BLOCKED_BUDGET'))


if __name__ == '__main__':
    unittest.main()
