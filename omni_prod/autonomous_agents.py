from __future__ import annotations
import json
from .model_gateway import OpenAICompatibleGateway
from .product_spec import ProductSpec
from .repository_patch import parse_patch
from .change_policy import ChangeAssessment

_ARCHITECT_SYSTEM = (
    "You are Omni Architect. Convert the user's product request to strict JSON. "
    "Return only JSON with title, summary, stack, requirements, acceptance. "
    "Every mandatory requirement must have at least one acceptance criterion. Include explicit quality, security, data and deployment requirements when relevant. "
    "Design for international use, accessibility, responsive behavior, safe secrets, observability and testability rather than a toy demo."
)
_GENERATOR_SYSTEM = (
    'You are Omni Code Generator. Return only JSON: '
    '{"files":[{"path":"...","content":"..."}]}. '
    'Generate a coherent runnable repository. Include .omni/project.json with build '
    'commands and verification commands mapped to acceptance_ids. Commands must be argv arrays, not shell strings. '
    'Never write outside the repository and never include secrets. Generate automated tests, README/setup, accessible responsive UI when relevant, i18n scaffolding, safe integration adapters, CI/deployment metadata, and production-grade error handling. Avoid generic AI-template styling; create a coherent design system appropriate to the product.'
)
_REPAIR_SYSTEM = (
    'You are Omni Repair Agent. Return only JSON: '
    '{"files":[{"path":"...","content":"... or null"}]}. '
    'Make the smallest safe patch that fixes supplied acceptance failures. '
    'Do not remove unrelated working behavior.'
)
_CHANGE_SYSTEM = (
    "Classify a user's follow-up against the approved spec. Return only JSON "
    "with category (system_bug|missing_requirement|change_request|ambiguous), "
    "reason, acceptance_ids. system_bug/missing_requirement must reference "
    "acceptance IDs already in the contract."
)

class ArchitectAgent:
    def __init__(self, gateway: OpenAICompatibleGateway):
        self.gateway = gateway
    def create_spec(self, prompt: str) -> ProductSpec:
        if not prompt.strip():
            raise ValueError('prompt cannot be empty')
        data = self.gateway.complete_json(system=_ARCHITECT_SYSTEM, user=prompt, max_tokens=6000)
        return ProductSpec.from_dict(data)

class GeneratorAgent:
    def __init__(self, gateway: OpenAICompatibleGateway):
        self.gateway = gateway
    def generate(self, spec: ProductSpec) -> tuple:
        data = self.gateway.complete_json(
            system=_GENERATOR_SYSTEM,
            user=json.dumps(spec.to_dict(), ensure_ascii=False),
            max_tokens=12000,
        )
        return parse_patch(data)

class RepairAgent:
    def __init__(self, gateway: OpenAICompatibleGateway):
        self.gateway = gateway
    def repair(self, *, spec: ProductSpec, repo_summary: dict, failures: list[dict]) -> tuple:
        payload = {'spec': spec.to_dict(), 'repository': repo_summary, 'failures': failures}
        data = self.gateway.complete_json(
            system=_REPAIR_SYSTEM,
            user=json.dumps(payload, ensure_ascii=False),
            max_tokens=10000,
        )
        return parse_patch(data)

class ChangeClassifierAgent:
    def __init__(self, gateway: OpenAICompatibleGateway):
        self.gateway = gateway
    def classify(self, *, spec: ProductSpec, followup: str) -> ChangeAssessment:
        payload = {'approved_spec': spec.to_dict(), 'followup': followup}
        data = self.gateway.complete_json(
            system=_CHANGE_SYSTEM,
            user=json.dumps(payload, ensure_ascii=False),
            max_tokens=2000,
        )
        return ChangeAssessment.from_dict(data, spec=spec)
