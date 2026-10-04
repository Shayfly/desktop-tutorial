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
    # M3 Revision 2: versioned preview contract, parsed by
    # preview_runtime.parse_preview_contract(). Build/verify keys are unchanged
    # (ProjectManifest ignores unknown keys).
    'The same .omni/project.json must also declare the running-preview contract exactly as: '
    '"schema_version": 2, "runtime": "python:3.11-slim" or "node:20-slim", '
    '"start": argv array that starts the app server, "port": integer the server listens on, '
    '"health_path": URL path that returns HTTP 200 once the app is ready (e.g. "/"). '
    'The preview container runs "start" from the repository root as committed: no install step runs first, '
    'the filesystem is read-only except /tmp, it runs as an unprivileged user, and it must listen on 0.0.0.0 '
    'at "port" (also provided as the PORT environment variable). Prefer a start command that needs only the '
    'runtime standard library. If the product cannot be served that way, omit the preview keys: the platform '
    'then reports the version as NOT_PREVIEWABLE instead of faking a preview. '
    'For a Web/SaaS product, the same .omni/project.json must also include a data-driven "web_saas_acceptance" object. '
    'It must contain "product_family":"managed_web_saas_v1", "required_kinds" covering auth, role, data_create, data_read, data_update, data_delete, integration, responsive, api_smoke, and non-empty "personas". '
    'Each persona has an id/role and HTTP steps. Every step has id, kind, acceptance_ids referencing only acceptance IDs from the approved ProductSpec, method, path and expect_status; optional headers/json/expect_json_contains/expect_text_contains/capture may be used. Use ${name} variables captured from earlier JSON responses so login/session and CRUD can be exercised end-to-end. Do not hard-code a showcase domain: derive paths and payloads from the generated product. '
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
