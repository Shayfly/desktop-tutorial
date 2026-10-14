import unittest
from decimal import Decimal

from omni_prod.memory_adapters import MemoryBuildRepository, MemoryArtifactStore, MemoryDeploymentRepository
from omni_prod.acceptance_pipeline import AcceptancePipeline
from omni_prod.orchestrator import BuildOrchestrator
from omni_prod.build_budget import BuildBudget
from omni_prod.retry import RetryPolicy
from omni_prod.models import BuildStatus
from omni_prod.artifact_keys import build_artifact_key
from omni_prod.secret_redaction import redact
from omni_prod.canary import CanaryPolicy

class AcceptanceHarnessTests(unittest.TestCase):
    def pipe(self, attempts=3, repairs=2):
        builds=MemoryBuildRepository(); artifacts=MemoryArtifactStore(); deployments=MemoryDeploymentRepository()
        orch=BuildOrchestrator(build_budget=BuildBudget(Decimal('5'),120,repairs),retry_policy=RetryPolicy(max_attempts=attempts))
        return AcceptancePipeline(builds=builds,artifacts=artifacts,deployments=deployments,orchestrator=orch),builds,artifacts,deployments

    def test_end_to_end_success(self):
        p,b,a,d=self.pipe()
        r=p.run(project_id='p1',version_id='v1',build_id='b1',execute=lambda n:(True,b'ZIPDATA'))
        self.assertEqual(r.status,'ready')
        self.assertEqual(b.get_status('b1'),BuildStatus.READY)
        self.assertEqual(a.get_bytes(r.artifact_key),b'ZIPDATA')
        self.assertEqual(d.current(project_id='p1',environment='production').version_id,'v1')

    def test_transient_failure_retries_then_succeeds(self):
        p,b,a,d=self.pipe(attempts=3)
        calls=[]
        def run(n):
            calls.append(n)
            return (False,'provider timeout') if n==1 else (True,b'ok')
        r=p.run(project_id='p',version_id='v',build_id='b',execute=run)
        self.assertEqual(r.status,'ready')
        self.assertEqual(calls,[1,2])

    def test_repair_path_then_succeeds(self):
        p,b,a,d=self.pipe(repairs=2)
        state={'fixed':False}
        def run(n): return (True,b'ok') if state['fixed'] else (False,'SyntaxError: x')
        def repair(msg,round_no): state['fixed']=True
        r=p.run(project_id='p',version_id='v',build_id='b',execute=run,repair=repair)
        self.assertEqual(r.status,'ready')
        self.assertIn('repair round 1',r.logs)

    def test_policy_failure_does_not_retry(self):
        p,b,a,d=self.pipe()
        r=p.run(project_id='p',version_id='v',build_id='b',execute=lambda n:(False,'policy violation: forbidden capability'))
        self.assertEqual(r.status,'failed')
        self.assertEqual(b.get_status('b'),BuildStatus.FAILED)

    def test_canary_bad_release_requests_rollback(self):
        p,*_=self.pipe()
        decision=p.canary_decision(policy=CanaryPolicy(min_requests=100,error_rate_threshold=.02),requests=1000,errors=30,current_percent=5)
        self.assertEqual(decision,'rollback')

class SecurityContractTests(unittest.TestCase):
    def test_artifact_key_blocks_traversal(self):
        with self.assertRaises(ValueError): build_artifact_key(project_id='../x',version_id='v',build_id='b')

    def test_log_redaction(self):
        text='Authorization: Bearer supersecret api_key=abc123 password=hunter2 postgresql://u:pw@db/x'
        red=redact(text)
        self.assertNotIn('supersecret',red)
        self.assertNotIn('abc123',red)
        self.assertNotIn('hunter2',red)
        self.assertNotIn(':pw@',red)

if __name__=='__main__': unittest.main()
