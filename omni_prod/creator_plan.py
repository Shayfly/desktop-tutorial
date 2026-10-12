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
from .customer_views import unpriced_capabilities
from .build_cost_plan import CostQuoteUnknown
from .qa_budget import QABudgetDenied
from .capability_worker import DEFAULT_NATIVE_BUILD_CAPABILITIES


def _infra_rows(contract, readiness: Mapping[str, Any]) -> list[dict]:
    kinds = dict((readiness or {}).get("kinds") or {})
    rows = []
    for requirement in contract.infrastructure:
        if getattr(requirement, "connection_mode", "") == "SELF_CONTAINED":
            # Embedded in the generated app (decision 2026-10-07 #27): nothing to
            # provision; verified only by the app's tests and preview acceptance.
            rows.append({
                "kind": requirement.kind, "purpose": requirement.purpose, "required": requirement.required,
                "readiness": "SELF_CONTAINED",
                "reason": "embedded in the generated app; verified only by its tests and preview acceptance",
            })
            continue
        state = kinds.get(requirement.kind) or {"status": "NOT_CONFIGURED", "reason": "no readiness reported"}
        rows.append({
            "kind": requirement.kind, "purpose": requirement.purpose, "required": requirement.required,
            "readiness": state.get("status"), "reason": state.get("reason"),
        })
    return rows


def _not_required(contract) -> list[dict]:
    """Infrastructure kinds this product did not ask for (demand-driven)."""
    from .infrastructure_registry import INFRASTRUCTURE_KINDS
    present = {r.kind for r in contract.infrastructure}
    return [{"kind": k, "status": "NOT_REQUIRED", "reason": "the product does not require it; not part of this build"}
            for k in INFRASTRUCTURE_KINDS if k not in present]


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

    # The quote is computed for admission parity, but its numbers are internal
    # unit economics and never returned (decision 2026-10-07 #29): the customer
    # sees only whether the build can be priced/authorized and why not.
    quote, quote_error, quote_error_code = None, None, None
    try:
        # Contract-aware cost plan (LLM + capabilities + infrastructure) when the
        # callable accepts the contract; zero-argument callables are legacy.
        quote = economics(contract) if inspect.signature(economics).parameters else economics()
    except CostQuoteUnknown as exc:
        names = unpriced_capabilities(exc.unknown)
        quote_error = ("A required capability is not available yet: " + ", ".join(names)) if names else \
            "A required capability is not available yet."
        quote_error_code = "cost_quote_unknown"
    except QABudgetDenied as exc:
        # INTERNAL_QA is an auditable founder-only staging entitlement. A
        # per-build/total ceiling is NOT a subscription-plan restriction.
        # Preserve its actionable reason rather than a misleading upsell.
        quote_error, quote_error_code = str(exc), "qa_budget_denied"
    except PermissionError:
        quote_error, quote_error_code = "This build is not available on your current plan.", "plan_cannot_authorize_cost"

    blockers: list[dict] = []
    if not durable_backend:
        blockers.append({"code": "durable_backend_not_configured",
                         "message": "Building needs the durable backend (PostgreSQL + S3 workspace) on this server."})
    for row in infrastructure:
        if row["required"] and row["readiness"] not in {"LIVE", "PARTIAL", "SELF_CONTAINED"}:
            blockers.append({"code": f"infrastructure_{row['kind']}_{str(row['readiness']).lower()}",
                             "message": f"{row['kind']}: {row['reason']}"})
    needs_image = any(c["key"] == "media.image.generate" and c["required"] for c in capabilities)
    if needs_image and (image_readiness or {}).get("status") != "PARTIAL":
        blockers.append({"code": f"image_provider_{str((image_readiness or {}).get('status', 'NOT_CONFIGURED')).lower()}",
                         "message": f"Product icon generation: {(image_readiness or {}).get('reason', 'not configured')}"})
    if quote_error:
        blockers.append({"code": quote_error_code, "message": quote_error})

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
        "infrastructure_not_required": _not_required(contract),
        "clarification_questions": [q.to_dict() for q in contract.unresolved_questions],
        "build_authorization": ("PRICED" if quote is not None else
                         "UNKNOWN" if quote_error_code == "cost_quote_unknown" else "NOT_AUTHORIZED"),
        "blockers": blockers,
        "can_build": ready and not blockers,
        "paid_work_started": False,
        "truth_note": ("Readiness PARTIAL means configured but not yet proven for this project. "
                       "Nothing is charged until you start the build."),
    }
