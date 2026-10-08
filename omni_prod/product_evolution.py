from __future__ import annotations
import json
from .model_gateway import OpenAICompatibleGateway
from .product_spec import ProductSpec
from .project_manifest import MANIFEST_SHAPE
from .dependency_policy import GENERATION_CONSTRAINTS
from .skills_runtime import guidance_for
from .repository_patch import parse_patch

# M4C: "change_request: DO NOT force it into RepairAgent... Implement a
# dedicated product-evolution path." RepairAgent's whole framing ("make the
# smallest safe patch that fixes supplied acceptance failures") needs failing
# acceptance ids to point at; ChangeAssessment.from_dict explicitly allows
# change_request to reference none at all (change_policy.py: only
# system_bug/missing_requirement require `ids`) -- "add a calendar view" is
# not a failing criterion, it is a capability that does not exist yet. This
# agent evolves the ProductSpec itself (adds new requirements/acceptance,
# never drops existing ones) alongside the patch that implements them, so
# spec and repository never drift apart -- the invariant M4B exists to
# protect (ProjectVersion N <-> ProductSpec N).

_EVOLUTION_SYSTEM = (
    'You are Omni Product Evolution. A user wants to ADD a new capability to '
    'an EXISTING, already-generated, already-accepted product. This is not a '
    'from-scratch build and not a bug fix -- do not regenerate the product. '
    'Return only JSON: {"spec": {"title":"...","summary":"...","stack":[...],'
    '"requirements":[{"id":"...","text":"...","kind":"functional|quality|security|data|deployment","mandatory":true}],'
    '"acceptance":[{"id":"...","requirement_id":"...","text":"..."}]}, '
    '"files": [{"path":"...","content":"... or null"}]}. '
    'The returned spec MUST repeat every existing requirement and acceptance '
    'criterion given to you unchanged, by the same id, plus any new ones the '
    'requested capability needs -- never drop, renumber, or reuse an existing '
    'id for something else. Write new requirement and acceptance texts in the '
    'same language as the existing spec. Every new mandatory requirement needs at least '
    'one new acceptance criterion, same rule as the original spec contract. '
    'The files patch applies on top of the existing repository, exactly like '
    'every other patch in this system (null content deletes a file); list '
    'only files that change, not the whole repository. Preserve the existing '
    'architecture, naming conventions, and file layout instead of '
    'restructuring the product for one new capability. Repository entries '
    'that include "content" are the full current file: edit from that content '
    'and return each changed file in full. Every new acceptance criterion '
    'needs an automated test, and its id must appear in the acceptance_ids of '
    'a verify entry in .omni/project.json -- return the full updated '
    '.omni/project.json whenever you add acceptance ids. '
    + MANIFEST_SHAPE
    + GENERATION_CONSTRAINTS
    + guidance_for('evolution')
)


class SpecRegressionError(ValueError):
    """Raised when a model response dropped an existing requirement/acceptance
    id instead of only adding to the spec -- the one invariant this agent
    checks itself rather than trusting the prompt instruction to hold, the
    same way repository_patch.apply_patch() re-validates paths itself instead
    of trusting every caller went through parse_patch() first."""


def _assert_no_dropped_ids(*, old: ProductSpec, new: ProductSpec) -> None:
    missing_req = {r.id for r in old.requirements} - {r.id for r in new.requirements}
    if missing_req:
        raise SpecRegressionError(f'evolution dropped existing requirement id(s): {sorted(missing_req)}')
    missing_acc = {a.id for a in old.acceptance} - {a.id for a in new.acceptance}
    if missing_acc:
        raise SpecRegressionError(f'evolution dropped existing acceptance id(s): {sorted(missing_acc)}')


class ProductEvolutionAgent:
    """The dedicated change_request execution path M4C requires. Same shape
    as ArchitectAgent/GeneratorAgent/RepairAgent (autonomous_agents.py): a
    thin wrapper over `OpenAICompatibleGateway.complete_json`, reusing
    `repository_patch.parse_patch` for the files half of the response -- no
    new patch format invented for this."""

    def __init__(self, gateway: OpenAICompatibleGateway):
        self.gateway = gateway

    def evolve(self, *, spec: ProductSpec, repo_summary: dict, followup: str) -> tuple[ProductSpec, tuple]:
        if not followup.strip():
            raise ValueError('followup cannot be empty')
        payload = {'spec': spec.to_dict(), 'repository': repo_summary, 'change_request': followup}
        data = self.gateway.complete_json(
            system=_EVOLUTION_SYSTEM, user=json.dumps(payload, ensure_ascii=False), max_tokens=14000,
        )
        new_spec = ProductSpec.from_dict(data.get('spec', {}))
        _assert_no_dropped_ids(old=spec, new=new_spec)
        patch = parse_patch({'files': data.get('files', [])})
        return new_spec, patch
