from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable
from .models import BuildStatus
from .orchestrator import BuildOrchestrator, OrchestrationState
from .artifact_keys import build_artifact_key
from .deployments import new_promotion
from .canary import CanaryPolicy, CanaryObservation, evaluate_canary
from .secret_redaction import redact

@dataclass(frozen=True)
class PipelineResult:
    status: str
    build_id: str
    artifact_key: str | None
    deployed_version: str | None
    logs: tuple[str,...]

class AcceptancePipeline:
    # Deterministic integration harness for the production control-plane contracts.
    def __init__(self, *, builds, artifacts, deployments, orchestrator: BuildOrchestrator):
        self.builds=builds; self.artifacts=artifacts; self.deployments=deployments; self.orchestrator=orchestrator

    def run(self, *, project_id: str, version_id: str, build_id: str,
            execute: Callable[[int], tuple[bool, bytes | str]],
            repair: Callable[[str,int], None] | None = None,
            environment: str='production') -> PipelineResult:
        logs=[]
        self.builds.create(build_id=build_id,project_id=project_id,version_id=version_id)
        if not self.builds.transition(build_id=build_id,expected=BuildStatus.QUEUED,target=BuildStatus.RUNNING):
            raise RuntimeError('failed to start build')
        state=OrchestrationState()
        while True:
            ok,payload=execute(state.attempt)
            if ok:
                if not isinstance(payload,(bytes,bytearray)): raise TypeError('successful build payload must be bytes')
                key=build_artifact_key(project_id=project_id,version_id=version_id,build_id=build_id)
                self.artifacts.put_bytes(key,bytes(payload))
                if not self.builds.transition(build_id=build_id,expected=BuildStatus.RUNNING,target=BuildStatus.READY,artifact_key=key):
                    raise RuntimeError('failed to finish build')
                promotion=new_promotion(project_id=project_id,version_id=version_id,build_id=build_id,environment=environment,artifact_key=key)
                self.deployments.promote(promotion)
                logs.append('build ready and promoted')
                return PipelineResult('ready',build_id,key,version_id,tuple(logs))
            message=str(payload)
            logs.append(redact(message))
            action=self.orchestrator.failure_action(state,message)
            if action=='retry':
                logs.append(f'retry attempt {state.attempt}')
                continue
            if action=='repair':
                if repair is None:
                    self.builds.transition(build_id=build_id,expected=BuildStatus.RUNNING,target=BuildStatus.FAILED,error_code='repair_unavailable',error_message=redact(message))
                    return PipelineResult('failed',build_id,None,None,tuple(logs))
                repair(message,state.budget.repair_rounds)
                logs.append(f'repair round {state.budget.repair_rounds}')
                continue
            self.builds.transition(build_id=build_id,expected=BuildStatus.RUNNING,target=BuildStatus.FAILED,error_code='build_failed',error_message=redact(message))
            return PipelineResult('failed',build_id,None,None,tuple(logs))

    def canary_decision(self, *, policy: CanaryPolicy, requests: int, errors: int, current_percent: int) -> str:
        return evaluate_canary(policy,CanaryObservation(requests=requests,errors=errors),current_percent)
