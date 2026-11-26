"""The owner, 2026-11-26 (10:13 and 10:20 UTC), on the real worker path and real PostgreSQL:

  * a build of the founder account is not stopped or cut by money: it spends past the old $2 per-build cap and
    completes; the same calls on another account stop at that account's budget (model_budget_exhausted);
  * a model WITHOUT a price does not fail a build: the build completes, the calls are recorded with their tokens and
    an UNKNOWN cost (task_attempts.metered_cost_usd NULL, never 0), and the build evidence names the model;
  * every build records what it cost us at the source (build_jobs.ai_cost, build_seconds; the cost_record);
  * the owner's cost report (omni_prod.owner_costs, GET /api/v28/owner/costs and /owner/costs) reads those rows back --
    per build, per stage, per repair round, per model, credits, the loss of a failed build, the conversation before a
    build, and the missing cost data -- and any other account is refused (403).

The worker runs worker_tasks._run_live_build_job with the real PostgresBuildRepository, PostgresSubscriptionService,
the real RoutedModelGateway (only the provider's HTTP answer is a double), the real budget binding and the real
attempt ledger. Runs in intake-budget-pg (skipped elsewhere without M4D2_DATABASE_URL)."""
from __future__ import annotations

import json
import os
import pathlib
import unittest
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
FOUNDER = 'usr_GCWlMxENgr9vpwph'          # pricing._FOUNDER_DEFAULT (not a secret)
SECRET_PROMPT = 'Build the bakery page of Ronit Example, phone 050-0000000'


def _catalog(priced: bool = True):
    from omni_prod.model_catalog import parse_model_catalog
    entry = {'name': 'writer', 'provider': 'labs', 'base_url': 'https://models.test/v1', 'model': 'writer-1',
             'api_key_env': 'WRITER_KEY', 'quality': 92, 'max_output_tokens': 300000}
    if priced:
        entry.update(input_per_million='1', output_per_million='10')
    return parse_model_catalog(json.dumps([entry]), {'WRITER_KEY': 'k'})


class _Provider:
    """The provider's HTTP answer (the only double): every call reports 1000 input and `out` output tokens."""
    out = 200_000

    def __init__(self, endpoint):
        self.endpoint, self.last_usage, self.last_response_model = endpoint, None, endpoint.model

    def complete_json(self, **kw):
        from omni_prod.provider_usage import ProviderUsage
        self.last_usage = ProviderUsage(provider='labs', model=self.endpoint.model, external=True, request_id='r',
                                        request_id_source='header', response_id='x', input_tokens=1000,
                                        output_tokens=_Provider.out, cached_tokens=0,
                                        provider_reported_cost_usd=None, usage_reported=True)
        return {'ok': True}


def _gateway(catalog):
    from omni_prod.model_policy import ModelUsePolicy
    from omni_prod.model_router import RoutingPolicy
    from omni_prod.routed_gateway import RoutedModelGateway
    return RoutedModelGateway(ranked=catalog, routing_policy=RoutingPolicy(minimum_quality=70),
                              policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                    external_budget_usd=Decimal('0.50'),
                                                    max_external_calls_per_build=150),
                              gateway_factory=_Provider, sleep=lambda s: None)


class OwnerCostsOnTheRealPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        root = pathlib.Path(__file__).resolve().parents[1]
        cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        cls.dbname = f'own_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(root / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url)
        cls.customer = f'usr_{uuid.uuid4().hex[:10]}'
        from omni_prod.subscription_store import PostgresSubscriptionService
        cls.subs = PostgresSubscriptionService(pool=cls.pool)
        with cls.pool.connection() as conn:
            for user, plan in ((FOUNDER, 'studio'), (cls.customer, 'studio')):
                conn.execute('INSERT INTO creator_accounts (id, email, password_hash, salt_b64) VALUES (%s,%s,%s,%s)',
                             (user, f'{user}@example.com', 'x', 'x'))
                conn.execute("INSERT INTO creator_subscriptions(user_id, plan_code, cycle, credits_used, "
                             "provider_spend_usd) VALUES (%s, %s, %s, 0, 0)", (user, plan, cls.subs._cycle_now()))
            conn.commit()
        cls.env = mock.patch.dict(os.environ, {'OMNI_FOUNDER_ACCOUNT_IDS': FOUNDER}, clear=False)
        cls.env.start()
        for name in ('OMNI_FOUNDER_NO_BUILD_LIMIT', 'OMNI_FOUNDER_BUILD_LLM_USD', 'OMNI_FOUNDER_CAP_EXEMPT'):
            os.environ.pop(name, None)
        cls.runs = {}
        cls.runs['owner'] = cls.run_build(FOUNDER, calls=4, llm_max='25', founder=True, intake=True)
        cls.runs['customer'] = cls.run_build(cls.customer, calls=4, llm_max='3.00', founder=False)
        cls.runs['unpriced'] = cls.run_build(cls.customer, calls=2, llm_max='5.00', founder=False, priced=False,
                                             out=1000)

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    @classmethod
    def run_build(cls, user, *, calls, llm_max, founder, priced=True, out=200_000, intake=False):
        from omni_prod import worker_tasks
        from omni_prod.attempt_ledger import TaskTaggedGateway
        from omni_prod.autonomous_core import ExecutionReport
        from omni_prod.job_repository import PostgresBuildRepository
        from omni_prod.rights_ip import GateStatus
        from tests.policy_fixtures import ACCEPTED_SPEC, verified_chain
        build_id, key, public = f'bld_{uuid.uuid4().hex}', f'tenant_{uuid.uuid4().hex[:8]}', f'prj_{uuid.uuid4().hex[:8]}'
        components = {'llm_maximum_usd': llm_max, 'cost_class': 'heavy', 'llm_class_cap_usd': '5.50'}
        if founder:
            components.update(founder_test=True, founder_no_build_limit=True)
        jobs = PostgresBuildRepository(cls.pool)
        if intake:      # the conversation that led to the owner's build: one settled call, one with unknown cost
            with cls.pool.connection() as conn:
                conn.execute("INSERT INTO intake_reservations (id, idempotency_key, account_id, project_id, lane, "
                             "quoted_usd, quote, state, cost_state, actual_usd, provider, model) VALUES "
                             "(%s, %s, %s, %s, 'production', 0.01, '{}'::jsonb, 'SETTLED', 'CONFIRMED', 0.0042, 'venice', "
                             "'gemini-3-5-flash-lite')", (f'ir_{uuid.uuid4().hex}', uuid.uuid4().hex, user, public))
                conn.execute("INSERT INTO intake_reservations (id, idempotency_key, account_id, project_id, lane, "
                             "quoted_usd, quote, state, cost_state, failure_reason, provider) VALUES "
                             "(%s, %s, %s, %s, 'production', 0.01, '{}'::jsonb, 'UNKNOWN', 'UNKNOWN', 'lost', 'venice')",
                             (f'ir_{uuid.uuid4().hex}', uuid.uuid4().hex, user, public))
                conn.commit()
        with cls.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    d = cls.subs.reserve(cur, build_id=build_id, user_id=user, project_id=key, cost_class='heavy',
                                         credits=500, estimated_provider_cost_usd=Decimal(llm_max))
                    assert d.allowed, d.reason
                    jobs.create_request(cur, build_id=build_id, user_id=user, internal_project_id=key,
                                        prompt=SECRET_PROMPT, target_markets=('IL',), branding_visible=None,
                                        white_label_name=None, rights_evidence=[], public_project_id=public)
                    jobs.create_with_cursor(cur, build_id=build_id, project_id=key, version_id='pending',
                                            evidence_json={'economics_quote': {'infrastructure_maximum_usd': '0',
                                                                               'components': components}},
                                            estimated_provider_cost_usd=Decimal(llm_max))
        _Provider.out = out
        gateway = _gateway(_catalog(priced))

        class _Engine:
            executor = verified_chain()

            def build(self, prompt):
                tagged = {t: TaskTaggedGateway(gateway, t) for t in ('architecture', 'codegen', 'repair')}
                tagged['architecture'].complete_json(system='s', user='u', max_tokens=out)
                for i in range(calls - 1):
                    tagged['codegen' if i == 0 else 'repair'].complete_json(system='s', user='u', max_tokens=out)
                report = ExecutionReport(passed=True, failures=(), build_log='log', tests_executed=2)
                return SimpleNamespace(status='ready', spec=ACCEPTED_SPEC, repair_rounds=max(0, calls - 2),
                                       repository={'app.py': 'x', '.omni/project.json': '{}'}, report=report)

        platform = mock.MagicMock()
        platform.subscriptions = cls.subs
        platform.brain.decide.return_value = SimpleNamespace(
            rights=SimpleNamespace(required_disclosures=()), creative='creative-plan', capabilities=None)
        platform.brain.creative.repository_files.return_value = {}
        platform.rights.assess.return_value = SimpleNamespace(publish_allowed=True, status=GateStatus.CLEAR,
                                                              to_dict=lambda: {'status': 'CLEAR'})
        platform.rights.repository_files.return_value = {}
        platform.branding.decorate_repository.side_effect = lambda repo, **kw: dict(repo)
        workspace = mock.MagicMock()
        workspace.commit.return_value = SimpleNamespace(id=f'ver_{uuid.uuid4().hex[:6]}', artifact_key='k.zip')
        gate = lambda passed, **x: SimpleNamespace(passed=passed, to_dict=lambda: {'passed': passed, **x}, **x)
        try:
            status = worker_tasks._run_live_build_job(
                build_id, jobs=jobs, platform=platform, workspace=workspace,
                components_factory=lambda: (_Engine(), gateway),
                quality_fn=lambda **kw: gate(True, score=90, minimum_score=80, blockers=()),
                security_fn=lambda repo: gate(True, findings=()), attempt_pool=cls.pool)
        except Exception as exc:          # a stopped build raises after writing FAILED, as in production
            status = f'raised:{type(exc).__name__}'
        worker_tasks._persist_build_attempts(cls.pool, jobs, build_id, gateway)
        return build_id, status

    def job(self, build_id):
        with self.pool.connection() as conn:
            row = conn.execute('SELECT status, error_code, ai_cost, actual_provider_cost_usd, build_seconds, '
                               'evidence_json FROM build_jobs WHERE id=%s', (build_id,)).fetchone()
        return row[0], row[1], Decimal(str(row[2])), row[3], row[4], row[5]

    def attempts(self, build_id):
        with self.pool.connection() as conn:
            return conn.execute("SELECT task_type, input_tokens, output_tokens, metered_cost_usd FROM task_attempts "
                                "WHERE build_id=%s AND kind='provider_call' ORDER BY attempt_seq", (build_id,)).fetchall()

    def report(self, **kw):
        from omni_prod.owner_costs import cost_report
        return cost_report(self.pool, days=kw.pop('days', 14), founder_ids={FOUNDER}, **kw)

    # -------------------------------------------------------------- limits
    def test_the_owner_build_spends_past_the_old_two_dollar_cap_and_completes(self):
        build_id, status = self.runs['owner']
        st, error, ai_cost, actual, seconds, evidence = self.job(build_id)
        self.assertEqual((status, st, error), ('ready', 'ready', None))
        rows = self.attempts(build_id)
        self.assertEqual(len(rows), 4)
        spent = sum((Decimal(str(r[3])) for r in rows), Decimal('0'))
        self.assertGreater(spent, Decimal('2'))                       # four calls of ~$2: no $2 cap
        self.assertEqual(ai_cost, spent.quantize(Decimal('0.000001')))   # recorded at the source
        self.assertIsNotNone(seconds)
        binding = evidence['model_budget_binding']
        self.assertEqual((binding['effective_budget_usd'], binding['effective_calls_per_build']), ('25', 400))
        self.assertTrue(binding['founder_no_build_limit'])
        self.assertEqual(evidence['economics_settlement']['cost_record']['basis'], 'ACTUAL')
        self.assertEqual(evidence['cost_data_missing'], [])
        near = {b['bound'] for b in evidence['economics_settlement']['cost_record']['bounds_near']}
        self.assertEqual(near, set())                                  # $8 of $25 is not near

    def test_another_account_with_the_same_calls_stops_at_its_budget(self):
        build_id, status = self.runs['customer']
        st, error, ai_cost, _, _, evidence = self.job(build_id)
        self.assertEqual((st, error), ('failed', 'model_budget_exhausted'))
        self.assertNotIn('founder_no_build_limit', evidence['model_budget_binding'])
        self.assertGreater(ai_cost, Decimal('0'))                      # what it spent before the stop is kept
        reasons = [e['reason'] for e in evidence['model_route_events']]
        self.assertTrue(any('output allowance cut' in x for x in reasons))  # its budget also CUT a call

    # -------------------------------------------------------- missing price
    def test_a_model_without_a_price_completes_and_records_an_unknown_cost_with_its_tokens(self):
        build_id, status = self.runs['unpriced']
        st, error, ai_cost, actual, _, evidence = self.job(build_id)
        self.assertEqual((status, st, error), ('ready', 'ready', None))
        rows = self.attempts(build_id)
        self.assertEqual(len(rows), 2)
        for task, tin, tout, metered in rows:
            self.assertEqual((tin, tout), (1000, 1000))                # the tokens are recorded
            self.assertIsNone(metered)                                 # the cost is unknown, never 0
        self.assertIsNone(actual)
        gaps = evidence['cost_data_missing']
        self.assertEqual([(g['kind'], g['name'], g['gap'], g['calls'], g['input_tokens'], g['output_tokens'])
                          for g in gaps], [('model', 'writer-1', 'price_missing', 2, 2000, 2000)])
        record = evidence['economics_settlement']['cost_record']
        self.assertFalse(record['complete'])
        self.assertEqual(record['unpriced_model_calls'], 2)
        self.assertEqual(Decimal(record['llm_usd']), Decimal('0'))    # the stand-in worst case is never a cost
        self.assertEqual(ai_cost, Decimal('0'))

    # --------------------------------------------------------------- report
    def test_the_report_reads_each_build_back_per_stage_round_model_and_credit(self):
        r = self.report()
        builds = {b['build_id']: b for b in r['builds']}
        owner = builds[self.runs['owner'][0]]
        spent = sum((Decimal(str(x[3])) for x in self.attempts(self.runs['owner'][0])), Decimal('0'))
        conversation = Decimal('0.0042')
        self.assertTrue(owner['owner_build'])
        self.assertEqual(Decimal(owner['provider_cost_known_usd']), spent + conversation)
        per_call = spent / 4
        self.assertEqual(Decimal(owner['stages']['architecture']['known_cost_usd']), per_call.quantize(Decimal('0.000001')))
        self.assertEqual(Decimal(owner['stages']['codegen']['known_cost_usd']), per_call.quantize(Decimal('0.000001')))
        self.assertEqual(Decimal(owner['stages']['repair']['known_cost_usd']), (2 * per_call).quantize(Decimal('0.000001')))
        self.assertEqual(owner['stages']['repair']['calls'], 2)
        self.assertEqual(sum(v['calls'] for v in owner['repair_rounds_cost'].values()), 2)
        self.assertEqual(owner['stages']['intake_conversation']['calls'], 2)
        self.assertEqual(owner['stages']['intake_conversation']['calls_without_cost'], 1)
        self.assertFalse(owner['cost_complete'])                       # the lost conversation call is unknown
        self.assertEqual(owner['models']['writer-1']['calls'], 4)
        self.assertEqual(owner['models']['writer-1']['output_tokens'], 4 * 200_000)
        self.assertEqual(owner['credits'], {'reserved': 500, 'reservation_status': 'SETTLED', 'funding_source': 'customer_plan',
                                            'charged': 500, 'released': 0})
        failed = builds[self.runs['customer'][0]]
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['credits']['charged'], 0)
        self.assertEqual(failed['credits']['released'], 500)
        self.assertGreater(Decimal(failed['loss_usd']), Decimal('0'))   # company_loss_events of the failed build
        self.assertEqual(Decimal(r['totals']['failed_builds_loss_usd']), Decimal(failed['loss_usd']))
        self.assertIn('ready', r['per_outcome'])
        self.assertIn('failed:model_budget_exhausted', r['per_outcome'])
        self.assertEqual(r['per_model']['writer-1']['builds'], 3)
        self.assertEqual(sum(v['builds'] for v in r['per_day'].values()), 3)
        owner_only = self.report(scope='owner')
        self.assertEqual([b['build_id'] for b in owner_only['builds']], [self.runs['owner'][0]])

    def test_the_report_names_the_missing_cost_data(self):
        r = self.report()
        names = {(g['kind'], g['name']): g for g in r['missing_cost_data']}
        model = names[('model', 'writer-1')]
        self.assertEqual((model['builds'], model['calls'], model['tokens']), (1, 2, 4000))
        self.assertIsNotNone(model['first_seen'])
        self.assertIn(('intake_model', 'venice'), names)
        unpriced = {b['build_id']: b for b in r['builds']}[self.runs['unpriced'][0]]
        self.assertEqual(unpriced['stages']['codegen']['calls_without_cost'], 1)
        self.assertFalse(unpriced['cost_complete'])

    def test_the_report_carries_no_personal_data(self):
        text = json.dumps(self.report())
        for secret in (FOUNDER, self.customer, SECRET_PROMPT, '@example.com', 'tenant_', 'prj_'):
            self.assertNotIn(secret, text)

    def test_the_route_serves_the_owner_and_refuses_every_other_account(self):
        from fastapi.testclient import TestClient
        from omni_prod import investor_app
        client = TestClient(investor_app.app)
        tokens = []
        for _ in range(2):
            reg = client.post('/api/v28/auth/register', json={'email': f'oc-{uuid.uuid4().hex[:10]}@example.com',
                                                               'password': 'correct-horse-battery'})
            self.assertEqual(reg.status_code, 200, reg.text)
            tokens.append(reg.json()['token'])
        owner_id = client.get('/api/v28/me', headers={'Authorization': 'Bearer ' + tokens[0]}).json()['id']
        with mock.patch.dict(os.environ, {'OMNI_FOUNDER_ACCOUNT_IDS': owner_id}), \
                mock.patch.object(investor_app, '_v28_pool', self.pool):
            ok = client.get('/api/v28/owner/costs?days=14', headers={'Authorization': 'Bearer ' + tokens[0]})
            self.assertEqual(ok.status_code, 200, ok.text)
            self.assertEqual(ok.json()['schema'], 'owner-costs/1')
            page = client.get('/owner/costs', headers={'Authorization': 'Bearer ' + tokens[0]})
            self.assertEqual(page.status_code, 200)
            self.assertIn('dir="rtl"', page.text)
            self.assertIn('נתוני עלות חסרים', page.text)
            for path in ('/api/v28/owner/costs', '/owner/costs'):
                other = client.get(path, headers={'Authorization': 'Bearer ' + tokens[1]})
                self.assertEqual(other.status_code, 403, path)
                self.assertNotIn('writer-1', other.text)
                self.assertEqual(client.get(path).status_code, 401, path)
            bad = client.get('/api/v28/owner/costs?days=900', headers={'Authorization': 'Bearer ' + tokens[0]})
            self.assertEqual(bad.status_code, 422)


if __name__ == '__main__':
    unittest.main()
