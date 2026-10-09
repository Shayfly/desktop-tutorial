from __future__ import annotations
import json

from .project_manifest import MANIFEST_SHAPE
from .model_gateway import OpenAICompatibleGateway
from .product_spec import ProductSpec
from .repository_patch import parse_patch
from .change_policy import ChangeAssessment
from .dependency_policy import GENERATION_CONSTRAINTS
from .skills_runtime import guidance_for

_ARCHITECT_SYSTEM = (
    "You are Omni Architect. Convert the user's product request to strict JSON. "
    "Return only JSON with title, summary, stack, requirements, acceptance. "
    # Founder feedback 2026-10-07: a Hebrew request produced an English
    # title/summary/requirements, shown to the customer as "what was built".
    # Golden E2E #1 build bld_85cc573b473341e9b3f10d248d743ff1 failed after five
    # repair rounds on criteria no sandbox test can check (Lighthouse score,
    # coverage percentage, browser localStorage, a JavaScript confirm dialog).
    "Every acceptance criterion must be checkable by an automated pytest test that runs in a sandbox with only the "
    "Python standard library, no browser and no network: phrase it through the app's HTTP responses (status codes, "
    "JSON, or text/elements present in the served HTML). Do not write criteria about Lighthouse or performance "
    "scores, test-coverage percentages, load tests, browser storage, visual appearance or JavaScript dialogs. "
    # Rehearsal 2026-10-08: "an SQL-injection attempt returns 400/500" contradicted
    # correct behaviour (parameterised queries store the text and answer 200).
    "Security criteria describe safe handling, not an error code: e.g. a name containing quotes or SQL is "
    "stored and shown as plain text and no other data changes. "
    "Use 3 to 6 acceptance criteria for a small product. "
    "Write title, summary, every requirement text and every acceptance text in the same language as the "
    "user's request (Hebrew request -> Hebrew text); keep ids, keys, kinds and stack names as specified. "
    # Golden E2E #1 on Preview (2026-10-07): without the exact shape the model
    # invented its own keys and the spec was rejected ("requirement id/text
    # required"). These are the keys ProductSpec.from_dict reads.
    'Use exactly this shape and these keys: {"title": "...", "summary": "...", "stack": ["..."], '
    '"requirements": [{"id": "R1", "text": "...", "kind": "functional", "mandatory": true}], '
    '"acceptance": [{"id": "A1", "requirement_id": "R1", "text": "..."}]}. '
    'kind is one of functional, quality, security, data, deployment. Requirement ids and acceptance ids are unique; '
    'every acceptance requirement_id names an existing requirement id. '
    "Every mandatory requirement must have at least one acceptance criterion. Include explicit quality, security, data and deployment requirements when relevant. "
    "Design for international use, accessibility, responsive behavior, safe secrets, observability and testability rather than a toy demo."
    + guidance_for('architect')
)
_GENERATOR_SYSTEM = (
    'You are Omni Code Generator. Return only JSON: '
    '{"files":[{"path":"...","content":"..."}]}. '
    'Generate a coherent runnable repository. Include .omni/project.json with build '
    'commands and verification commands mapped to acceptance_ids. Commands must be argv arrays, not shell strings. '
    + MANIFEST_SHAPE +
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
    'runtime standard library. GET / must serve the complete user interface as an HTML page (forms, buttons, '
    'tables, in the language of the request, dir="rtl" for Hebrew) that calls JSON endpoints served by the same '
    'app; a health string or placeholder at / is rejected. Automated tests must exercise the HTTP endpoints and '
    'the served page (start the server on a free port in the test, or call the handler), not only internal '
    'classes, so every acceptance criterion is checked through the product as a user reaches it. '
    'Every product here is a website or web app, so the preview keys are required; '
    'the platform starts the app in the sandbox and checks health_path before accepting the build. '
    'For a Web/SaaS product, the same .omni/project.json must also include a data-driven "web_saas_acceptance" object. '
    'It must contain "product_family":"managed_web_saas_v1", "required_kinds" listing the kinds this product really has from auth, role, data_create, data_read, data_update, data_delete, integration, responsive, api_smoke (auth and role only when the product has sign-in or roles), and non-empty "personas". '
    # Decision 2026-10-07 #27: a self-contained app has no external integration
    # or background infrastructure; such steps would be NOT_VERIFIED, not passed.
    'The plan is run against the real app inside the build and every failing step is sent back for repair, so its test data must be valid under the product\'s own rules (dates from today within the allowed window, phone numbers in local format, unique values where duplicates are refused) and expect_text_contains must quote text the page really shows. Never write a fixed calendar date in a step: use ${today}, ${date_plus_N} or ${date_minus_N} (N days from the day the plan runs), which the platform fills in. '
    'When the approved spec stack is self-contained (embedded SQLite), omit the integration kind and any external-integration or background-job steps: they are out of scope and are reported as not verified. '
    'Each persona has an id/role and HTTP steps. Every step has id, kind, acceptance_ids referencing only acceptance IDs from the approved ProductSpec, method, path and expect_status; optional headers/json/expect_json_contains/expect_text_contains/capture may be used. Use ${name} variables captured from earlier JSON responses so login/session and CRUD can be exercised end-to-end. Do not hard-code a showcase domain: derive paths and payloads from the generated product. '
    'Never write outside the repository and never include secrets. Generate automated tests, README/setup, accessible responsive UI when relevant, i18n scaffolding, safe integration adapters, CI/deployment metadata, and production-grade error handling. Avoid generic AI-template styling; create a coherent design system appropriate to the product. '
    + GENERATION_CONSTRAINTS
    + guidance_for('generator')
)
_REPAIR_SYSTEM = (
    'You are Omni Repair Agent. Return only JSON: '
    '{"files":[{"path":"...","content":"... or null"}]}. '
    'Make the smallest safe patch that fixes supplied acceptance failures. '
    'Repository entries that include "content" are the full current file: edit from that content and '
    'return each changed file in full. '
    + MANIFEST_SHAPE +
    'Do not remove unrelated working behavior. '
    'Never special-case particular test values (names, dates, ids, phone numbers) in product code to make a check pass; '
    'fix the general behaviour. If an acceptance step itself uses data that is invalid under the approved rules '
    '(for example a past or fixed date), correct that step in .omni/project.json -- use ${today} or ${date_plus_N} '
    'for dates -- and keep the rule in the app. '
    'You must write actual tests. If you fail to use pytest/jest, the build '
    'will be rejected permanently. '
    + GENERATION_CONSTRAINTS
    + guidance_for('repair')
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
        **({'content_note': repo_summary['content_note']} if 'content_note' in repo_summary else {}),
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
    def create_spec(self, prompt: str, *, deterministic_floor: dict | None = None) -> ProductSpec:
        if not prompt.strip():
            raise ValueError('prompt cannot be empty')
        user = prompt
        if deterministic_floor is not None:
            user = json.dumps({
                'user_prompt': prompt,
                'deterministic_floor': deterministic_floor,
                'instruction': 'Enrich the product specification without removing or weakening any deterministic minimum.',
            }, ensure_ascii=False)
        data = self.gateway.complete_json(system=_ARCHITECT_SYSTEM, user=user, max_tokens=6000)
        try:
            return ProductSpec.from_dict(data)
        except (ValueError, TypeError, AttributeError) as first_error:
            # One corrective round with the validator's exact complaint; a
            # second invalid answer fails the build explicitly. Both calls are
            # ordinary recorded, budget-checked model calls.
            correction = json.dumps({
                'original_request': user,
                'invalid_specification': data,
                'validation_error': str(first_error)[:500],
                'instruction': 'Return the corrected specification as JSON with exactly the required shape and keys.',
            }, ensure_ascii=False, default=str)
            data = self.gateway.complete_json(system=_ARCHITECT_SYSTEM, user=correction, max_tokens=6000)
            try:
                return ProductSpec.from_dict(data)
            except (ValueError, TypeError, AttributeError) as second_error:
                raise ValueError(f'architect returned an invalid specification twice: {second_error} '
                                 f'(first: {first_error})') from second_error

class GeneratorAgent:
    def __init__(self, gateway: OpenAICompatibleGateway):
        self.gateway = gateway
    def generate(self, spec: ProductSpec) -> tuple:
        data = self.gateway.complete_json(
            system=_GENERATOR_SYSTEM,
            user=json.dumps(spec.to_dict(), ensure_ascii=False),
            # Rehearsal 37840698696: with the quality skills the code is longer
            # and 12k output tokens truncated the JSON on every model.
            max_tokens=24000,
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
            max_tokens=20000,
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
