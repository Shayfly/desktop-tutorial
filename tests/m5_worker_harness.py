"""Shared fastapi-free harness for driving worker_tasks._run_live_build_job.

Used by the M5 Task 6-9 tests. Everything external is a test double; nothing
here is evidence that a real provider, database or sandbox is LIVE.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from omni_prod import worker_tasks
from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.models import BuildStatus
from omni_prod.rights_ip import GateStatus


class FakeJobs:
    def __init__(self, request):
        self.request = request
        self.transitions: list[dict] = []

    def get_request(self, build_id):
        return self.request

    def transition(self, **kw):
        self.transitions.append(kw)
        return True


def _gate(passed, **extra):
    data = {'passed': passed, **extra}
    return SimpleNamespace(passed=passed, to_dict=lambda: data, **extra)


class ContractBuildHarness:
    def __init__(self, contract=None, *, verified=True, gateway=None, engine_exc=None, prompt='Build a todo app'):
        request = {
            'user_id': 'usr_1', 'internal_project_id': 'tenant_abc', 'prompt': prompt,
            'target_markets': ('US',), 'branding_visible': None, 'white_label_name': None,
            'rights_evidence': [], 'public_project_id': contract.project_id if contract else 'proj_public',
        }
        if contract is not None:
            request.update({
                'build_contract': contract.to_dict(), 'build_contract_id': contract.id,
                'build_contract_fingerprint': contract.contract_fingerprint,
                'build_contract_binding': 'BOUND',
            })
        self.jobs = FakeJobs(request)
        self.subs = MagicMock()
        self.subs.plan_for.return_value = SimpleNamespace(code='pro')
        self.platform = MagicMock()
        self.platform.subscriptions = self.subs
        self.platform.brain.decide.return_value = SimpleNamespace(
            rights=SimpleNamespace(required_disclosures=()), creative='creative-plan', capabilities=None)
        self.platform.brain.creative.repository_files.return_value = {'.148ai/creative.json': '{}'}
        self.platform.rights.assess.return_value = SimpleNamespace(
            publish_allowed=True, status=GateStatus.CLEAR, to_dict=lambda: {'status': 'CLEAR'})
        self.platform.rights.repository_files.return_value = {'RIGHTS.md': 'r'}
        self.platform.branding.decorate_repository.side_effect = lambda repo, **kw: dict(repo)
        self.workspace = MagicMock()
        self.workspace.commit.return_value = SimpleNamespace(id='ver_1', artifact_key='repositories/abc.zip')
        self.gateway = gateway if gateway is not None else SimpleNamespace(
            state=SimpleNamespace(external_spend_usd=Decimal('0'), external_calls=0), events=[])
        report = ExecutionReport(
            passed=verified,
            failures=() if verified else (AcceptanceFailure('AC-1', 'tests failed', 'E'),),
            build_log='log')
        self.result = SimpleNamespace(
            status='ready' if verified else 'failed', spec='spec',
            repository={'app.py': 'x', '.omni/project.json': '{}'}, repair_rounds=0, report=report)
        self.engine_builds = 0
        self.engine_exc = engine_exc

        harness = self

        class _Engine:
            def build(self, prompt):
                harness.engine_builds += 1
                if harness.engine_exc is not None:
                    raise harness.engine_exc
                return harness.result

        self.engine = _Engine()
        self.quality = _gate(True, score=90, minimum_score=80, blockers=())
        self.security = _gate(True, findings=())

    def factory(self):
        return self.engine, self.gateway

    def run(self, **extra):
        return worker_tasks._run_live_build_job(
            'bld_1', jobs=self.jobs, platform=self.platform, workspace=self.workspace,
            components_factory=self.factory, quality_fn=lambda **kw: self.quality,
            security_fn=lambda repo: self.security, **extra)

    @property
    def final(self):
        return self.jobs.transitions[-1]


__all__ = ['ContractBuildHarness', 'FakeJobs', 'BuildStatus']
