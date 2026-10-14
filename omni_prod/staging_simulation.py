from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

from .acceptance_pipeline import AcceptancePipeline
from .build_budget import BuildBudget
from .canary import CanaryObservation, CanaryPolicy
from .canary_controller import CanaryState, next_canary_state
from .memory_adapters import (
    MemoryArtifactStore,
    MemoryBuildRepository,
    MemoryDeploymentRepository,
)
from .orchestrator import BuildOrchestrator
from .retry import RetryPolicy

@dataclass(frozen=True)
class StagingSimulationResult:
    build_status: str
    final_canary_status: str
    final_canary_percent: int
    deployments: int
    artifacts: int

def run_staging_simulation() -> StagingSimulationResult:
    builds = MemoryBuildRepository()
    artifacts = MemoryArtifactStore()
    deployments = MemoryDeploymentRepository()
    orchestrator = BuildOrchestrator(
        build_budget=BuildBudget(
            max_ai_cost=Decimal("10"),
            max_build_seconds=300,
            max_repair_rounds=2,
        ),
        retry_policy=RetryPolicy(max_attempts=3),
    )
    pipe = AcceptancePipeline(
        builds=builds,
        artifacts=artifacts,
        deployments=deployments,
        orchestrator=orchestrator,
    )

    calls = []
    def execute(attempt: int):
        calls.append(attempt)
        if attempt == 1:
            return False, "provider timeout"
        return True, b"SIMULATED-IMMUTABLE-APP-ARTIFACT"

    result = pipe.run(
        project_id="staging-project",
        version_id="v16",
        build_id="build-v16",
        execute=execute,
        environment="staging",
    )
    if result.status != "ready" or calls != [1, 2]:
        raise RuntimeError("staging build simulation failed")

    policy = CanaryPolicy(
        initial_percent=5,
        step_percent=35,
        error_rate_threshold=0.02,
        min_requests=100,
    )
    state = CanaryState(percent=policy.initial_percent, status="running")
    for obs in (
        CanaryObservation(requests=200, errors=1),
        CanaryObservation(requests=300, errors=2),
        CanaryObservation(requests=500, errors=2),
    ):
        state = next_canary_state(policy, state, obs)
    if state.status != "complete" or state.percent != 100:
        raise RuntimeError("canary did not complete")

    return StagingSimulationResult(
        build_status=result.status,
        final_canary_status=state.status,
        final_canary_percent=state.percent,
        deployments=len(deployments.history),
        artifacts=len(artifacts.objects),
    )
