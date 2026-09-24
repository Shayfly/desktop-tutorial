import json
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from omni_prod.agent_team import AgentRole, plan_team
from omni_prod.benchmark_suite import CASES, BenchmarkRunner, BenchmarkResult
from omni_prod.billing import CreditLedger, classify_charge
from omni_prod.demo_project import demo_spec, create_demo_repository
from omni_prod.design_system import derive_tokens, anti_template_fingerprint
from omni_prod.deployment_runtime import AutoscalingPolicy, international_default_topology
from omni_prod.game_pipeline import engine_plan
from omni_prod.i18n import SUPPORTED_LOCALES, direction, LocaleConfig
from omni_prod.integrations import REGISTRY, IntegrationBinding
from omni_prod.international_readiness import payload
from omni_prod.investor_app import app
from omni_prod.mobile_pipeline import build_plan
from omni_prod.product_analytics import BuildMetric, summarize
from omni_prod.project_memory import ProjectMemory
from omni_prod.quality_gate import assess_repository
from omni_prod.security_testing import hostile_repository_scan
from omni_prod.teams import Membership, can, require
from omni_prod.workspace import ProjectWorkspace

class QualityTests(unittest.TestCase):
    def test_demo_repository_clears_quality_gate(self):
        spec=demo_spec('Build a serious CRM')
        repo=create_demo_repository('Build a serious CRM',spec)
        q=assess_repository(spec=spec,repository=repo,minimum_score=75)
        self.assertTrue(q.passed, q.to_dict())
        self.assertGreaterEqual(q.score,75)
    def test_missing_manifest_is_blocker(self):
        spec=demo_spec('Build CRM')
        q=assess_repository(spec=spec,repository={'README.md':'x'},minimum_score=1)
        self.assertFalse(q.passed)
        self.assertTrue(q.blockers)
    def test_hardcoded_secret_blocks_security(self):
        spec=demo_spec('Build CRM'); repo=create_demo_repository('Build CRM',spec)
        repo['bad.py']='STRIPE_SECRET_KEY="sk_test_abcdefghijklmnopqrstuvwxyz"'
        self.assertFalse(hostile_repository_scan(repo).passed)

class WorkspaceMemoryTests(unittest.TestCase):
    def test_immutable_versions_and_restore(self):
        w=ProjectWorkspace(); v1=w.commit(project_id='p',repository={'a':'1'},message='first')
        v2=w.commit(project_id='p',repository={'a':'2'},message='second')
        v3=w.restore(project_id='p',version_id=v1.id)
        self.assertEqual(v3.repository(),{'a':'1'}); self.assertEqual(v3.parent_id,v2.id)
    def test_checksums_change_with_content(self):
        w=ProjectWorkspace(); a=w.commit(project_id='p',repository={'a':'1'},message='x'); b=w.commit(project_id='p',repository={'a':'2'},message='y')
        self.assertNotEqual(a.checksum,b.checksum)
    def test_memory_context_recent_and_bounded(self):
        m=ProjectMemory(max_entries=3)
        for i in range(5): m.append(project_id='p',kind='decision',text=f'decision {i}')
        self.assertEqual(len(m.list('p')),3); self.assertIn('decision 4',m.context('p'))

class CommercialTests(unittest.TestCase):
    def test_rbac(self):
        dev=Membership('o','u','developer'); self.assertTrue(can(dev,'deploy')); self.assertFalse(can(dev,'billing'))
        with self.assertRaises(PermissionError): require(dev,'billing')
    def test_system_bug_is_free(self):
        d=classify_charge(category='system_bug',estimated_compute_units=50); self.assertFalse(d.billable); self.assertEqual(d.credits,0)
    def test_change_request_consumes_credits(self):
        ledger=CreditLedger(10); d=classify_charge(category='change_request',estimated_compute_units=3)
        self.assertEqual(ledger.apply(d),7)
    def test_missing_requirement_is_free(self):
        self.assertFalse(classify_charge(category='missing_requirement').billable)

class InternationalizationTests(unittest.TestCase):
    def test_locale_catalog(self): self.assertGreaterEqual(len(SUPPORTED_LOCALES),10)
    def test_rtl(self): self.assertEqual(direction('he'),'rtl'); self.assertEqual(direction('ar'),'rtl'); self.assertEqual(direction('en'),'ltr')
    def test_invalid_default_locale(self):
        with self.assertRaises(ValueError): LocaleConfig(default_locale='xx',enabled=('xx',))

class IntegrationTests(unittest.TestCase):
    def test_catalog_is_broad(self): self.assertGreaterEqual(len(REGISTRY),8)
    def test_raw_secret_rejected(self):
        with self.assertRaises(ValueError): IntegrationBinding.bind('stripe',{'STRIPE_SECRET_KEY':'sk_live_real','STRIPE_WEBHOOK_SECRET':'whsec_real'})
    def test_secret_refs_accepted(self):
        b=IntegrationBinding.bind('stripe',{'STRIPE_SECRET_KEY':'env:STRIPE_SECRET_KEY','STRIPE_WEBHOOK_SECRET':'vault:stripe/webhook'})
        self.assertEqual(b.provider,'stripe')

class TargetPipelineTests(unittest.TestCase):
    def test_android_contract(self): self.assertEqual(build_plan('android').store_artifact,'aab')
    def test_ios_contract(self): self.assertEqual(build_plan('ios').store_artifact,'ipa')
    def test_mobile_invalid(self):
        with self.assertRaises(ValueError): build_plan('windows-phone')
    def test_all_game_engines(self):
        self.assertEqual({engine_plan(x).engine for x in ('godot','unity','unreal')},{'godot','unity','unreal'})

class DesignAgentTests(unittest.TestCase):
    def test_design_is_deterministic(self): self.assertEqual(derive_tokens('abc'),derive_tokens('abc'))
    def test_design_varies(self): self.assertNotEqual(anti_template_fingerprint(derive_tokens('alpha')),anti_template_fingerprint(derive_tokens('beta')))
    def test_agent_team_contains_security_qa_devops(self):
        p=plan_team(target='game',has_mobile=True,has_game=True); roles={x.role for x in p.tasks}
        self.assertTrue({AgentRole.QA,AgentRole.SECURITY,AgentRole.DEVOPS,AgentRole.MOBILE,AgentRole.GAME}.issubset(roles))

class BenchmarkAnalyticsTests(unittest.TestCase):
    def test_benchmark_catalog_200(self): self.assertGreaterEqual(len(CASES),200); self.assertEqual(len({x.id for x in CASES}),len(CASES))
    def test_benchmark_has_20_categories(self): self.assertGreaterEqual(len({x.category for x in CASES}),20)
    def test_benchmark_summary(self):
        r=[BenchmarkResult('1','x','ready',1,100,5),BenchmarkResult('2','x','failed',2,200,3)]
        s=BenchmarkRunner.summarize(r); self.assertEqual(s['success_rate'],.5)
    def test_product_metrics(self):
        p=summarize([BuildMetric('ready',100,1,.1,90),BuildMetric('failed',500,3,.2,50)])
        self.assertEqual(p.success_rate,.5); self.assertEqual(p.avg_cost_per_ready_usd,.1)

class RuntimeSecurityTests(unittest.TestCase):
    def test_autoscaling_validation(self):
        with self.assertRaises(ValueError): AutoscalingPolicy(min_replicas=3,max_replicas=2)
    def test_topology_scales_workers(self):
        t=international_default_topology(); self.assertGreater(t.worker_replicas.max_replicas,t.worker_replicas.min_replicas)
    def test_shell_manifest_flagged(self):
        spec=demo_spec('xxy'); repo=create_demo_repository('xxy',spec)
        m=json.loads(repo['.omni/project.json']); m['verify'][0]['argv']=['bash','-lc','echo hi']; repo['.omni/project.json']=json.dumps(m)
        self.assertFalse(hostile_repository_scan(repo).passed)

class InternationalReadinessTests(unittest.TestCase):
    def test_readiness_is_truthful(self):
        d=payload(); self.assertEqual(d['total'],len(d['gates'])); self.assertTrue(any(not g['live_verified'] for g in d['gates']))
        self.assertTrue(all('evidence' in g for g in d['gates']))

class ApiTests(unittest.TestCase):
    def setUp(self): self.c=TestClient(app)
    def test_status_exposes_v24_release(self):
        d=self.c.get('/api/status').json(); self.assertEqual(d['product_release'],'V24 International Readiness'); self.assertGreaterEqual(d['benchmark_catalog_cases'],200)
    def test_demo_build_has_quality_security_version(self):
        d=self.c.post('/api/demo/build',json={'prompt':'Build an international CRM','project_id':'p-api'}).json()
        self.assertEqual(d['status'],'ready'); self.assertTrue(d['quality']['passed']); self.assertTrue(d['security']['passed']); self.assertIn('checksum',d['version'])
    def test_history_and_memory(self):
        self.c.post('/api/demo/build',json={'prompt':'Build booking','project_id':'history-api'})
        h=self.c.get('/api/projects/history-api/history').json(); m=self.c.get('/api/projects/history-api/memory').json()
        self.assertGreaterEqual(len(h['versions']),1); self.assertIn('Build booking',m['context'])
    def test_integrations_endpoint(self): self.assertGreaterEqual(len(self.c.get('/api/integrations').json()['providers']),8)
    def test_benchmark_endpoint_limits(self): self.assertEqual(len(self.c.get('/api/benchmark/catalog?limit=3').json()['cases']),3)
    def test_targets(self):
        self.assertEqual(self.c.get('/api/targets/mobile/android').json()['store_artifact'],'aab')
        self.assertEqual(self.c.get('/api/targets/game/unreal').json()['engine'],'unreal')
    def test_bug_billing_endpoint(self): self.assertFalse(self.c.post('/api/billing/classify',json={'category':'system_bug','estimated_compute_units':100}).json()['billable'])

if __name__=='__main__': unittest.main()

class DependencyV24Tests(unittest.TestCase):
    def test_extras_exact_pin_is_locked(self):
        from omni_prod.dependency_inventory import parse_requirements, lock_status
        d=parse_requirements('psycopg[binary,pool]==3.3.6\n')
        self.assertTrue(lock_status(d)['locked']); self.assertEqual(d[0].pinned_version,'3.3.6')

class CspAssetTests(unittest.TestCase):
    def test_control_center_uses_external_assets(self):
        c=TestClient(app); r=c.get('/')
        self.assertIn('/assets/app.css',r.text); self.assertIn('/assets/app.js',r.text)
        self.assertNotIn('<style>',r.text); self.assertNotIn('<script>',r.text)
        self.assertEqual(c.get('/assets/app.js').status_code,200)
        self.assertEqual(c.get('/assets/app.css').status_code,200)
        self.assertIn("default-src 'self'",r.headers.get('content-security-policy',''))

class LearningLoopTests(unittest.TestCase):
    def test_training_export_redacts_secrets(self):
        from omni_prod.training_data import TrainingExample,to_jsonl
        out=to_jsonl([TrainingExample('repair','api_key=SUPERSECRET123','token=ABCDEF123456789','repaired',90)])
        self.assertIn('[REDACTED]',out); self.assertNotIn('SUPERSECRET123',out)
    def test_human_eval_summary(self):
        from omni_prod.human_evaluation import HumanEvaluation,summarize_evaluations
        d=summarize_evaluations([HumanEvaluation('p','b1',True,5),HumanEvaluation('p','b2',False,3)])
        self.assertEqual(d['satisfaction_rate'],.5); self.assertEqual(d['avg_score'],4)

class OfflineStarterFactoryTests(unittest.TestCase):
    def test_demo_varies_by_product_category(self):
        from omni_prod.demo_project import classify_demo_category, demo_spec, create_demo_repository
        self.assertEqual(classify_demo_category('Build an ecommerce store with checkout'),'commerce')
        self.assertEqual(classify_demo_category('Build a CRM for technicians'),'crm')
        s=demo_spec('Build an ecommerce store with checkout'); r=create_demo_repository('Build an ecommerce store with checkout',s)
        domain=json.loads(r['domain.json']); self.assertEqual(domain['category'],'commerce'); self.assertIn('Cart',domain['modules'])
        self.assertIn('openapi.json',r); self.assertIn('schema.sql',r)
