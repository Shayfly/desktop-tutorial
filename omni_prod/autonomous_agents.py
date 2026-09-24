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
    'Do not remove unrelated working behavior. '
    'You must write actual tests. If you fail to use pytest/jest, the build '
    'will be rejected permanently.'
)

# M2 Revision 4 (native adaptation): repo_summary is already a lightweight
# {path, chars} listing (see AutonomousProductEngine._summary), never file
# content, but a large generated tree (a stray node_modules/, build output,
# a vendored binary) can still bloat that listing with entries that give the
# repair model nothing useful to act on. Filtered out before being sent, and
# capped, so the prompt stays focused on files the model can actually fix.
_NOISY_PATH_PREFIXES = ('node_modules/', '.git/', 'dist/', 'build/', '__pycache__/', '.venv/', 'venv/')
_NOISY_SUFFIXES = ('.png', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.woff2', '.zip', '.tar', '.gz', '.pdf', '.mp4', '.mp3')
_MAX_REPAIR_FILE_ENTRIES = 300

def _filter_repo_summary(repo_summary: dict) -> dict:
    files = repo_summary.get('files', [])
    kept = [
        f for f in files
        if not str(f.get('path', '')).startswith(_NOISY_PATH_PREFIXES)
        and not str(f.get('path', '')).lower().endswith(_NOISY_SUFFIXES)
    ][:_MAX_REPAIR_FILE_ENTRIES]
    return {
        'file_count': repo_summary.get('file_count'),
        'total_chars': repo_summary.get('total_chars'),
        'files': kept,
        'files_omitted_from_prompt': max(0, len(files) - len(kept)),
    }
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
        payload = {'spec': spec.to_dict(), 'repository': _filter_repo_summary(repo_summary), 'failures': failures}
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
