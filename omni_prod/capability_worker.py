from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Mapping

from .capabilities import CapabilityPlan
from .capability_executor import CapabilityExecutionAssignment, CapabilityExecutionSummary


class CapabilityStageBlocked(RuntimeError):
    def __init__(self, message: str, *, evidence: Mapping | None = None) -> None:
        super().__init__(message)
        self.evidence = dict(evidence or {})


# These are capabilities whose evidence is produced by the existing durable
# software build pipeline itself, not by a second external provider call.
DEFAULT_NATIVE_BUILD_CAPABILITIES = frozenset({
    'software.plan', 'software.architecture', 'software.code.generate',
    'software.dependencies.install', 'software.build', 'software.test',
    'software.repair', 'software.preview', 'software.export',
    'target.web', 'target.saas', 'target.backend', 'target.database',
})


@dataclass
class DurableCapabilityBuildStage:
    repository: object
    native_capability_keys: set[str] | frozenset[str] = DEFAULT_NATIVE_BUILD_CAPABILITIES
    executor: object | None = None
    assignments_resolver: Callable[[CapabilityPlan], Mapping[str, CapabilityExecutionAssignment]] | None = None

    def _snapshot(self, build_id: str) -> dict:
        rows = self.repository.requirements(build_id=build_id)
        required_ready = all(
            (not bool(row['required'])) or row['status'] in {'VERIFIED', 'PLANNED'}
            for row in rows
        )
        failed = [r for r in rows if r['status'] in {'FAILED', 'BLOCKED', 'NOT_CONFIGURED'}]
        return {
            'status': 'BLOCKED' if any(r['required'] for r in failed) else ('PARTIAL' if failed else 'READY_FOR_BUILD'),
            'required_ready': required_ready and not any(r['required'] for r in failed),
            'requirements': [
                {
                    'requirement_id': r['requirement_id'], 'capability_key': r['capability_key'],
                    'required': bool(r['required']), 'status': r['status'],
                    'selected_provider': r.get('selected_provider'),
                    'pricing_version': r.get('pricing_version'),
                    'artifact_key': r.get('artifact_key'),
                    'verification': dict(r.get('verification') or {}),
                }
                for r in rows
            ],
            'usage': (self.repository.usage_for_build(build_id=build_id)
                      if hasattr(self.repository, 'usage_for_build') else []),
        }

    def prepare(
        self, *, build_id: str, project_id: str, plan: CapabilityPlan,
        authorized_maximum_usd: Decimal, now: float,
    ) -> dict:
        authorized = Decimal(str(authorized_maximum_usd))
        if authorized < 0:
            raise CapabilityStageBlocked('invalid capability authorization ceiling')
        self.repository.create_plan(build_id=build_id, plan=plan)
        assignments = dict(self.assignments_resolver(plan)) if self.assignments_resolver else {}

        external_requirements = [r for r in plan.requirements if r.key not in self.native_capability_keys]
        unresolved = []
        for requirement in external_requirements:
            assignment = assignments.get(requirement.id)
            if assignment is None:
                row = next(r for r in self.repository.requirements(build_id=build_id)
                           if r['requirement_id'] == requirement.id)
                target = 'NOT_CONFIGURED' if requirement.required else 'SKIPPED'
                self.repository.transition(
                    build_id=build_id, requirement_id=requirement.id,
                    expected=row['status'], target=target,
                )
                if requirement.required:
                    unresolved.append(requirement)

        if unresolved:
            evidence = self._snapshot(build_id)
            names = ', '.join(r.key for r in unresolved)
            raise CapabilityStageBlocked(
                f'required capability NOT_CONFIGURED: {names}', evidence=evidence,
            )

        assigned_requirements = [r for r in external_requirements if r.id in assignments]
        if assigned_requirements:
            if self.executor is None:
                raise CapabilityStageBlocked(
                    'provider assignments exist but capability executor is NOT_CONFIGURED',
                    evidence=self._snapshot(build_id),
                )
            maximum = sum((assignments[r.id].quote.maximum_cost_usd for r in assigned_requirements), Decimal('0'))
            if maximum > authorized:
                raise CapabilityStageBlocked(
                    f'capability maximum {maximum} exceeds durable authorization {authorized}',
                    evidence=self._snapshot(build_id),
                )
            # External capability dependency closure is already present in the
            # canonical plan.  Only external nodes execute here; native software
            # lifecycle evidence is finalized after the existing build gates.
            external_ids = {r.id for r in assigned_requirements}
            external_plan = CapabilityPlan(
                requirements=tuple(
                    type(r)(
                        id=r.id, key=r.key, purpose=r.purpose, required=r.required,
                        quantity=r.quantity, constraints=r.constraints,
                        dependency_ids=tuple(dep for dep in r.dependency_ids if dep in external_ids),
                    )
                    for r in assigned_requirements
                ),
                target_keys=tuple(k for k in plan.target_keys if any(r.key == k for r in assigned_requirements)),
                notes=tuple(plan.notes) + ('external-provider-stage',),
            )
            summary: CapabilityExecutionSummary = self.executor.execute_plan(
                build_id=build_id, project_id=project_id, plan=external_plan,
                assignments={rid: assignments[rid] for rid in external_ids}, now=now,
            )
            if summary.status == 'FAILED':
                raise CapabilityStageBlocked('required capability execution failed', evidence=self._snapshot(build_id))

        return self._snapshot(build_id)

    def finalize_native(self, *, build_id: str, plan: CapabilityPlan, core_ready: bool, evidence: Mapping | None = None) -> dict:
        rows = {r['requirement_id']: r for r in self.repository.requirements(build_id=build_id)}
        for requirement in plan.requirements:
            if requirement.key not in self.native_capability_keys:
                continue
            row = rows[requirement.id]
            if row['status'] == 'VERIFIED':
                continue
            target = 'VERIFIED' if core_ready else ('FAILED' if requirement.required else 'SKIPPED')
            self.repository.transition(
                build_id=build_id, requirement_id=requirement.id,
                expected=row['status'], target=target,
                verification=dict(evidence or {}),
            )
        snapshot = self._snapshot(build_id)
        # After native finalization PLANNED is not a ready state.
        rows2 = self.repository.requirements(build_id=build_id)
        snapshot['required_ready'] = all(
            (not bool(r['required'])) or r['status'] == 'VERIFIED' for r in rows2
        )
        snapshot['status'] = 'VERIFIED' if snapshot['required_ready'] else 'BLOCKED'
        return snapshot
