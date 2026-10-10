from __future__ import annotations

import unittest
from tests.policy_fixtures import ACCEPTED_SPEC, verified_chain
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.capability_repository import MemoryCapabilityRepository
from omni_prod.models import BuildStatus
from omni_prod import worker_tasks


class FakeJobs:
    def __init__(self, plan):
        self.request = {
            'user_id': 'u1', 'internal_project_id': 'tenant-a', 'prompt': 'build product',
            'target_markets': ('US',), 'branding_visible': None, 'white_label_name': None,
            'rights_evidence': [], 'public_project_id': 'proj-a',
            'authorized_provider_cost_usd': Decimal('1.00'),
        }
        self.plan = plan
        self.transitions = []
    def get_request(self, build_id): return self.request
    def transition(self, **kw):
        self.transitions.append(kw)
        return True


class BlockingStage:
    def __init__(self): self.calls=[]
    def prepare(self, **kw):
        self.calls.append(('prepare', kw))
        from omni_prod.capability_worker import CapabilityStageBlocked
        raise CapabilityStageBlocked('media.3d.mesh.generate is NOT_CONFIGURED', evidence={
            'required_ready': False,
            'requirements': [{'capability_key':'media.3d.mesh.generate','status':'NOT_CONFIGURED'}],
        })


class PassingStage:
    def __init__(self): self.calls=[]
    def prepare(self, **kw):
        self.calls.append(('prepare', kw))
        return {'required_ready': True, 'status': 'VERIFIED', 'requirements': []}
    def finalize_native(self, **kw):
        self.calls.append(('finalize_native', kw))
        return {'required_ready': True, 'status': 'VERIFIED', 'requirements': []}


def plan_with_3d():
    return CapabilityPlan((
        CapabilityRequirement('cap-plan','software.plan','plan',True),
        CapabilityRequirement('cap-3d','media.3d.mesh.generate','mesh',True),
    ), ())


def platform_for(plan):
    p=MagicMock()
    p.subscriptions=MagicMock()
    p.subscriptions.plan_for.return_value=SimpleNamespace(code='pro')
    p.brain.decide.return_value=SimpleNamespace(
        capabilities=plan, rights=SimpleNamespace(required_disclosures=()), creative='creative')
    p.brain.creative.repository_files.return_value={}
    p.rights.assess.return_value=SimpleNamespace(
        publish_allowed=True, status=SimpleNamespace(value='CLEAR'), to_dict=lambda:{'status':'CLEAR'})
    p.rights.repository_files.return_value={}
    p.branding.decorate_repository.side_effect=lambda repo,**kw: dict(repo)
    return p


def passing_engine():
    report=SimpleNamespace(passed=True, failures=(), build_log='ok')
    return SimpleNamespace(executor=verified_chain(), build=lambda prompt: SimpleNamespace(
        status='ready', report=report, spec=ACCEPTED_SPEC, repository={'app.py':'x'}, repair_rounds=0))


class WorkerCapabilityGateTests(unittest.TestCase):
    def test_required_not_configured_capability_blocks_before_engine_and_is_actionable(self):
        plan=plan_with_3d(); jobs=FakeJobs(plan); platform=platform_for(plan); stage=BlockingStage()
        engine=MagicMock(wraps=passing_engine())
        with self.assertRaisesRegex(Exception, 'NOT_CONFIGURED'):
            worker_tasks._run_live_build_job(
                'b1', jobs=jobs, platform=platform, workspace=MagicMock(),
                components_factory=lambda:(engine, None),
                quality_fn=lambda **kw: SimpleNamespace(passed=True, score=100, minimum_score=80, blockers=(), to_dict=lambda:{}),
                security_fn=lambda repo: SimpleNamespace(passed=True, findings=(), to_dict=lambda:{}),
                capability_stage=stage,
            )
        engine.build.assert_not_called()
        final=jobs.transitions[-1]
        self.assertEqual(final['target'], BuildStatus.FAILED)
        self.assertEqual(final['error_code'], 'capability_not_configured')
        self.assertFalse(final['evidence_json']['capabilities']['required_ready'])

    def test_capability_stage_runs_before_engine_and_finalize_does_not_change_gate_order(self):
        plan=CapabilityPlan((CapabilityRequirement('cap-plan','software.plan','plan',True),),())
        jobs=FakeJobs(plan); platform=platform_for(plan); stage=PassingStage(); order=[]
        engine=passing_engine()
        orig_build=engine.build
        engine.build=lambda prompt:(order.append('engine') or orig_build(prompt))
        quality=lambda **kw:(order.append('quality') or SimpleNamespace(passed=True,score=100,minimum_score=80,blockers=(),to_dict=lambda:{'passed':True}))
        security=lambda repo:(order.append('security') or SimpleNamespace(passed=True,findings=(),to_dict=lambda:{'passed':True}))
        workspace=MagicMock(); workspace.commit.return_value=SimpleNamespace(id='v1', artifact_key='a.zip')
        out=worker_tasks._run_live_build_job(
            'b1', jobs=jobs, platform=platform, workspace=workspace,
            components_factory=lambda:(engine,None), quality_fn=quality, security_fn=security,
            capability_stage=stage,
        )
        self.assertEqual(out, 'ready')
        self.assertEqual(stage.calls[0][0], 'prepare')
        self.assertEqual(stage.calls[-1][0], 'finalize_native')
        self.assertEqual(order, ['engine','quality','security'])
        self.assertEqual(jobs.transitions[-1]['target'], BuildStatus.READY)
        self.assertTrue(jobs.transitions[-1]['evidence_json']['capabilities']['required_ready'])
        manifest_call = platform.brain.creative.repository_files.call_args
        self.assertEqual(manifest_call.kwargs['capability_evidence']['status'], 'VERIFIED')


class DurableCapabilityStageTests(unittest.TestCase):
    def test_missing_optional_external_is_skipped_but_required_missing_blocks(self):
        from omni_prod.capability_worker import DurableCapabilityBuildStage, CapabilityStageBlocked
        repo=MemoryCapabilityRepository()
        stage=DurableCapabilityBuildStage(repository=repo, native_capability_keys={'software.plan'})
        optional=CapabilityPlan((
            CapabilityRequirement('native','software.plan','plan',True),
            CapabilityRequirement('optional','media.image.generate','hero',False),
        ),())
        ev=stage.prepare(build_id='b1', project_id='p1', plan=optional,
                         authorized_maximum_usd=Decimal('1'), now=1)
        rows={r['requirement_id']:r for r in repo.requirements(build_id='b1')}
        self.assertEqual(rows['optional']['status'],'SKIPPED')
        self.assertTrue(ev['required_ready'])

        repo2=MemoryCapabilityRepository()
        stage2=DurableCapabilityBuildStage(repository=repo2, native_capability_keys={'software.plan'})
        required=CapabilityPlan((
            CapabilityRequirement('native','software.plan','plan',True),
            CapabilityRequirement('required','media.image.generate','icon',True),
        ),())
        with self.assertRaises(CapabilityStageBlocked):
            stage2.prepare(build_id='b2', project_id='p1', plan=required,
                           authorized_maximum_usd=Decimal('1'), now=1)

    def test_assignment_maximum_cannot_exceed_durable_authorization(self):
        from omni_prod.capability_worker import DurableCapabilityBuildStage, CapabilityStageBlocked
        from omni_prod.capability_executor import CapabilityExecutionAssignment
        from omni_prod.provider_contracts import ProviderQuote
        repo=MemoryCapabilityRepository()
        req=CapabilityRequirement('img','media.image.generate','icon',True)
        plan=CapabilityPlan((req,),())
        quote=ProviderQuote('p','media.image.generate',Decimal('0.5'),Decimal('2.0'),'pv','asset',Decimal('1'))
        stage=DurableCapabilityBuildStage(
            repository=repo, native_capability_keys=set(), executor=MagicMock(),
            assignments_resolver=lambda p:{'img':CapabilityExecutionAssignment('p',quote)},
        )
        with self.assertRaisesRegex(CapabilityStageBlocked,'authorization'):
            stage.prepare(build_id='b3', project_id='p1', plan=plan,
                          authorized_maximum_usd=Decimal('1'), now=1)
        stage.executor.execute_plan.assert_not_called()


if __name__=='__main__': unittest.main()
