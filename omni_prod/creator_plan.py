"""M5-UX01: plan + quote preview shown to the creator before any paid work.

Compiles (and durably saves) the next Build Contract revision for a prompt,
then reports what 148AI understood, which capabilities and infrastructure the
product needs, the conservative cost authorization and every named blocker.
Nothing here reserves credits, calls a model provider or enqueues work: the
creator confirms first, then POST .../builds runs with this build_contract_id.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Mapping

from .build_contract import BuildContractStatus
from .capability_worker import DEFAULT_NATIVE_BUILD_CAPABILITIES


def _infra_rows(contract, readiness: Mapping[str, Any]) -> list[dict]:
    kinds = dict((readiness or {}).get("kinds") or {})
    rows = []
    for requirement in contract.infrastructure:
        state = kinds.get(requirement.kind) or {"status": "NOT_CONFIGURED", "reason": "no readiness reported"}
        rows.append({
            "kind": requirement.kind, "purpose": requirement.purpose, "required": requirement.required,
            "readiness": state.get("status"), "reason": state.get("reason"),
        })
    return rows


def build_plan_preview(
    *,
    architect,
    repository,
    project_id: str,
    prompt: str,
    economics: Callable[..., Any],
    durable_backend: bool,
    infrastructure_readiness: Mapping[str, Any],
    image_readiness: Mapping[str, Any],
) -> dict:
    latest = repository.latest(project_id)
    next_version = 1 if latest is None else latest.contract_version + 1
    contract = architect.compile(prompt, project_id=project_id, contract_version=next_version)
    repository.save(contract)

    capabilities = [
        {"key": r.key, "purpose": r.purpose, "required": r.required,
         "executed_by": "build pipeline" if r.key in DEFAULT_NATIVE_BUILD_CAPABILITIES else "external provider"}
        for r in contract.capability_plan.requirements
    ]
    infrastructure = _infra_rows(contract, infrastructure_readiness)

    quote, quote_error = None, None
    try:
        # Contract-aware cost plan (LLM + capabilities + infrastructure) when the
        # callable accepts the contract; zero-argument callables are legacy.
        quote = economics(contract) if inspect.signature(economics).parameters else economics()
    except PermissionError as exc:
        quote_error = str(exc)

    blockers: list[dict] = []
    if not durable_backend:
        blockers.append({"code": "durable_backend_not_configured",
                         "message": "Building needs the durable backend (PostgreSQL + S3 workspace) on this server."})
    for row in infrastructure:
        if row["required"] and row["readiness"] not in {"LIVE", "PARTIAL"}:
            blockers.append({"code": f"infrastructure_{row['kind']}_{str(row['readiness']).lower()}",
                             "message": f"{row['kind']}: {row['reason']}"})
    needs_image = any(c["key"] == "media.image.generate" and c["required"] for c in capabilities)
    if needs_image and (image_readiness or {}).get("status") != "PARTIAL":
        blockers.append({"code": f"image_provider_{str((image_readiness or {}).get('status', 'NOT_CONFIGURED')).lower()}",
                         "message": f"Product icon generation: {(image_readiness or {}).get('reason', 'not configured')}"})
    if quote_error:
        blockers.append({"code": "plan_cannot_authorize_cost", "message": quote_error})

    ready = contract.status == BuildContractStatus.READY
    return {
        "build_contract_id": contract.id,
        "contract_version": contract.contract_version,
        "contract_fingerprint": contract.contract_fingerprint,
        "status": contract.status.value,
        "product": {
            "title": contract.product_spec.title, "summary": contract.product_spec.summary,
            "family": contract.product_family, "target": contract.target, "release_target": contract.release_target,
            "user_roles": list(contract.user_roles), "data_requirements": list(contract.data_requirements),
            "required_integrations": list(contract.required_integrations),
        },
        "capabilities": capabilities,
        "infrastructure": infrastructure,
        "clarification_questions": [q.to_dict() for q in contract.unresolved_questions],
        "economics": None if quote is None else quote.to_dict(),
        "economics_error": quote_error,
        "estimated_cost_usd": None if quote is None else str(quote.total_estimated_variable_usd),
        "maximum_authorized_cost_usd": None if quote is None else str(quote.total_authorized_variable_usd),
        "blockers": blockers,
        "can_build": ready and not blockers,
        "paid_work_started": False,
        "truth_note": ("Readiness PARTIAL means configured but not yet proven for this project. "
                       "Nothing is charged until you start the build."),
    }
