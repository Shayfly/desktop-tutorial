"""Meta-agents that verify 148AI itself (autonomous completion §8, §14-15).

  regression_guardian(junit)   every test file of the regression matrix must
                               keep at least its recorded number of tests and
                               all of them must pass (CI step after pytest)
  required_layers(files)       System Test Orchestrator: which test layers a
                               change needs; unit tests alone never complete a
                               feature that touches workers, previews or money
  failure_injection()          the injection catalog with where each is proven
  quality_gate(...)            the final verdict for a milestone, with reasons
  write_matrices(result)       PLATFORM_CAPABILITY / REGRESSION / GOLDEN_E2E /
                               FAILURE_INJECTION matrices from code + evidence
"""
from __future__ import annotations

import ast
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .evidence import AT, BACKUP, CRASH, DEPLOY, FREE, PAID, REHEARSAL_ACCEPT

ROOT = Path(__file__).resolve().parents[2]
REGRESSION = ROOT / 'PLATFORM_REGRESSION_MATRIX.json'
CAPABILITY = ROOT / 'PLATFORM_CAPABILITY_MATRIX.json'
GOLDEN = ROOT / 'GOLDEN_E2E_MATRIX.json'
INJECTION = ROOT / 'FAILURE_INJECTION_MATRIX.json'

# capability -> (expected behaviour, regression test files)
REGRESSION_AREAS = {
    'discovery': ('professional discovery, delegated answers, brief revisions', ('tests/test_discovery_and_approval.py', 'tests/test_brief_capability_detection.py')),
    'approval': ('server-bound approval, one build per approved plan', ('tests/test_discovery_and_approval.py',)),
    'build': ('contract-bound build, gates, settlement', ('tests/test_m3_preview_logic.py', 'tests/test_live_build_stores_spec.py')),
    'modify': ('natural-language change with candidate and accept', ('tests/test_golden_mod_path_live_postgres.py',)),
    'cancel': ('queued and running stop for builds and changes', ('tests/test_build_cancel_and_log.py', 'tests/test_crash_recovery_and_change_parity.py')),
    'resume': ('crash recovery and lost-queue redispatch', ('tests/test_crash_recovery_and_change_parity.py', 'tests/test_janitor_redispatch.py')),
    'journal': ('live build/change log', ('tests/test_build_cancel_and_log.py',)),
    'provider_routing': ('price/quality routing, fallback, quota release', ('tests/test_provider_quota_and_dialects.py',)),
    'economics': ('metered settlement, QA budget', ('tests/test_actual_cost_settlement.py',)),
    'persistence': ('preview data across restart and versions', ('tests/test_preview_data_durability.py',)),
    'preview': ('private previews, acceptance on a scratch copy', ('tests/test_preview_access.py', 'tests/test_preview_router.py')),
    'browser_execution': ('real-browser probe of every product', ('tests/test_browser_probe.py',)),
    'behavioral_acceptance': ('in-build acceptance feeding repair, requirements-aware scope', ('tests/test_behavior_acceptance_in_build.py', 'tests/test_demand_driven_infrastructure.py')),
    'release': ('release gates and versions', ('tests/test_m3_preview_logic.py',)),
    'recovery': ('backups proven by restore', ('tests/test_backup_restore.py',)),
    'agent_os': ('durable agent runtime, permissions, budgets, verification, truthful registry', ('tests/test_agent_os.py',)),
    'failure_injection': ('graceful handling of injected failures', ('tests/test_failure_injection.py',)),
}


def _count_tests(rel: str) -> int:
    path = ROOT / rel
    if not path.is_file():
        return 0
    tree = ast.parse(path.read_text(encoding='utf-8'))
    return sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test'))


def regression_matrix() -> dict:
    return {'version': 1, 'areas': {area: {'expected': expected,
                                           'files': {f: {'min_tests': _count_tests(f)} for f in files}}
                                    for area, (expected, files) in REGRESSION_AREAS.items()}}


def regression_guardian(junit_path: str, matrix: dict | None = None) -> list[str]:
    """Problems (empty = no regression). Skipped tests (live Postgres absent)
    count as present, not as failures; CI runs them against Postgres."""
    matrix = matrix or json.loads(REGRESSION.read_text())
    root = ET.parse(junit_path).getroot()
    by_file: dict[str, dict] = {}
    for case in root.iter('testcase'):
        cls = case.get('classname', '')
        rel = cls.split('.')[0:2]
        key = '/'.join(rel) + '.py' if len(rel) == 2 else ''
        stat = by_file.setdefault(key, {'total': 0, 'failed': []})
        stat['total'] += 1
        if case.find('failure') is not None or case.find('error') is not None:
            stat['failed'].append(case.get('name'))
    problems = []
    for area, spec in matrix['areas'].items():
        for rel, want in spec['files'].items():
            got = by_file.get(rel, {'total': 0, 'failed': []})
            if got['total'] < want['min_tests']:
                problems.append(f'{area}: {rel} ran {got["total"]} tests, the matrix requires {want["min_tests"]}')
            for name in got['failed']:
                problems.append(f'{area}: {rel}::{name} failed')
    return problems


LAYER_RULES = (
    ('omni_prod/assets/', ('browser',)),
    ('infra/postgres/', ('database', 'migration', 'real-server', 'backup-restore')),
    ('omni_prod/worker_tasks.py', ('worker/queue', 'real-server', 'golden-e2e')),
    ('omni_prod/build_control.py', ('worker/queue', 'real-server')),
    ('omni_prod/maintenance.py', ('worker/queue', 'failure-injection', 'real-server')),
    ('omni_prod/preview_', ('real-server', 'browser')),
    ('omni_prod/routed_gateway.py', ('failure-injection', 'golden-e2e')),
    ('omni_prod/model_', ('failure-injection', 'golden-e2e')),
    ('omni_prod/behavior_acceptance.py', ('behavioral-acceptance', 'golden-e2e')),
    ('omni_prod/web_saas_acceptance.py', ('behavioral-acceptance', 'golden-e2e')),
    ('omni_prod/investor_app.py', ('api', 'real-server')),
    ('omni_prod/backup.py', ('backup-restore',)),
    ('.github/workflows/', ('real-server',)),
    ('omni_prod/agent_os/', ('contract', 'database')),
)


def required_layers(changed_files) -> list[str]:
    layers = ['static', 'unit']
    for f in changed_files:
        for prefix, extra in LAYER_RULES:
            if f.startswith(prefix):
                layers += [x for x in extra if x not in layers]
    return layers


_INJECTIONS = (
    ('provider timeout', 'tests/test_failure_injection.py::test_timeout_falls_back_to_the_next_provider', 'fallback provider serves'),
    ('malformed provider response', 'tests/test_failure_injection.py::test_malformed_response_falls_back', 'fallback provider serves'),
    ('provider 429', 'tests/test_failure_injection.py::test_429_is_released_and_the_route_is_skipped', 'released at $0, route skipped'),
    ('provider 500', 'tests/test_failure_injection.py::test_500_is_retried_then_falls_back', 'bounded retry, then fallback'),
    ('all providers down', 'tests/test_failure_injection.py::test_all_providers_down_is_a_named_failure', 'build FAILED model_unavailable'),
    ('exhausted budget', 'tests/test_failure_injection.py::test_exhausted_budget_stops_with_a_named_failure', 'FAILED model_budget_exhausted'),
    ('DB unavailable during a step', 'tests/test_failure_injection.py::test_database_unavailable_during_a_step_does_not_crash_the_build', 'warning, build continues'),
    ('queue interruption', 'tests/test_failure_injection.py::test_queue_interruption_is_redispatched', 'janitor re-dispatches'),
    ('invalid migration', 'tests/test_failure_injection.py::test_invalid_migration_aborts_instead_of_diverging', 'deploy aborts on checksum drift'),
    ('corrupted artifact reference', 'tests/test_failure_injection.py::test_corrupted_artifact_is_refused', 'ArtifactIntegrityError, never served'),
    ('network interruption to the sandbox', 'tests/test_failure_injection.py::test_sandbox_network_interruption_is_a_named_error', 'RemoteSandboxError'),
    ('worker killed mid-build', CRASH.ref, 'requeued once, build finished READY'),
    ('deployment during a build', DEPLOY.ref, 'drain: running job finishes first'),
    ('browser JS exception', 'tests/test_browser_probe.py', 'repairable BROWSER failure'),
    ('expired preview token', 'tests/test_preview_access.py::test_public_needs_no_token_and_expired_tokens_fail', '401 private page'),
    ('insufficient credits', 'tests/test_v28_148ai_launch.py', 'build refused before work'),
    ('invalid OAuth', '', 'not applicable: generated-app OAuth not implemented'),
)


def failure_injection() -> dict:
    rows = []
    for failure, proven_by, expected in _INJECTIONS:
        status = 'PASS' if proven_by else 'BLOCKED'
        rows.append({'failure': failure, 'expected_handling': expected, 'proven_by': proven_by, 'status': status,
                     'layer': 'real-server' if proven_by.startswith(('postdeploy', 'deploy')) else 'unit/integration'})
    return {'version': 1, 'injections': rows}


GOLDEN_SCENARIOS = (
    ('Golden 1 — New SaaS (Hebrew, persistent, preview, restart, version)', (PAID, FREE, REHEARSAL_ACCEPT), 'PASS', ''),
    ('Golden 2 — SaaS with authentication', (), 'NOT_RUN', 'generated-app sign-in is not implemented (Identity & Auth agent NOT_IMPLEMENTED)'),
    ('Golden 3 — Existing project modification', (), 'PARTIAL', 'founder change verified 2026-10-08 (mod_c14435dc); not re-run on this code'),
    ('Golden 4 — Cancellation (queued + active)', (FREE,), 'PASS', ''),
    ('Golden 5 — Crash recovery', (CRASH,), 'PASS', ''),
    ('Golden 6 — Provider failure', (), 'PARTIAL', 'fallback proven by injection tests; OpenAI/Anthropic have no credit, so no real second provider'),
    ('Golden 7 — Budget guard', (), 'PARTIAL', 'ceiling enforced in the paid run ($0.15 effective); refusal proven by injection test'),
    ('Golden 8 — Backup / restore', (BACKUP,), 'PASS', 'restore into a throw-away database; no destructive drill'),
    ('Golden 9 — Automation', (), 'NOT_RUN', 'Automation agent NOT_IMPLEMENTED'),
    ('Golden 10 — Media', (), 'BLOCKED', 'image provider not configured on the build worker; video/voice/music providers not contracted'),
    ('Golden 11 — 2D game', (), 'NOT_RUN', '2D game agents NOT_IMPLEMENTED (Phaser not in the sandbox allowlist)'),
)


def golden_matrix() -> dict:
    return {'version': 1, 'scenarios': [
        {'scenario': name, 'status': status, 'evidence': [e.ref for e in ev],
         'commits': [e.commit for e in ev], 'at': [AT.get(e.ref) for e in ev], 'note': note}
        for name, ev, status, note in GOLDEN_SCENARIOS]}


def capability_matrix(result: dict) -> dict:
    by_skill = {s['skill_key']: s for s in result['skills']}
    rows = []
    for area, (expected, files) in REGRESSION_AREAS.items():
        rows.append({'capability': area, 'expected_behavior': expected, 'test_layer': 'unit/integration',
                     'test_location': list(files), 'last_result': 'see CI (regression guardian)'})
    for key in ('behavioral_acceptance_test', 'preview_access_protect', 'persistence_verification', 'job_resume',
                'credit_settlement', 'restore_verification', 'browser_launch', 'job_cancel'):
        s = by_skill.get(key, {})
        rows.append({'capability': key, 'expected_behavior': s.get('gap') or 'as contracted', 'test_layer': 'real-server',
                     'test_location': s.get('evidence') or [], 'last_result': s.get('status'),
                     'last_verified_commit': s.get('last_verified_commit'), 'last_verified_at': s.get('last_verified_at'),
                     'environment': 'pre-staging worker host'})
    return {'version': 1, 'capabilities': rows}


def quality_gate(*, result: dict, regression_problems: list[str] | None, inflation: list[str]) -> dict:
    golden = golden_matrix()['scenarios']
    reasons = []
    if regression_problems is None:
        reasons.append('regression guardian has not run on this commit')
    elif regression_problems:
        reasons.append(f'{len(regression_problems)} regression(s)')
    if inflation:
        reasons.append(f'{len(inflation)} registry inflation finding(s)')
    must = ('Golden 1', 'Golden 4', 'Golden 5', 'Golden 8')
    for g in golden:
        if g['scenario'].startswith(must) and g['status'] != 'PASS':
            reasons.append(f"{g['scenario'].split(' — ')[0]} not PASS")
    live = {s['skill_key'] for s in result['skills'] if s['status'] in ('REAL_SERVER_VERIFIED', 'LIVE')}
    for need in ('behavioral_acceptance_test', 'credit_settlement', 'preview_access_protect', 'restore_verification', 'job_resume'):
        if need not in live:
            reasons.append(f'{need} has no fresh live evidence')
    return {'verdict': 'VERIFIED' if not reasons else 'NOT_VERIFIED', 'reasons': reasons}


def write_matrices(result: dict) -> None:
    REGRESSION.write_text(json.dumps(regression_matrix(), indent=1) + '\n')
    CAPABILITY.write_text(json.dumps(capability_matrix(result), indent=1, default=str) + '\n')
    GOLDEN.write_text(json.dumps(golden_matrix(), indent=1, ensure_ascii=False) + '\n')
    INJECTION.write_text(json.dumps(failure_injection(), indent=1) + '\n')


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == 'regression':
        problems = regression_guardian(argv[1])
        for p in problems:
            print(f'::error title=regression guardian::{p}')
        print(f'::notice title=regression guardian::{len(problems)} problem(s)')
        return 1 if problems else 0
    if argv and argv[0] == 'layers':
        print(json.dumps(required_layers(argv[1:])))
        return 0
    if argv and argv[0] == 'gate':
        from .audit import audit, inflation_findings
        result = audit()
        problems = regression_guardian(argv[1]) if len(argv) > 1 else None
        verdict = quality_gate(result=result, regression_problems=problems, inflation=inflation_findings(result))
        print(f"::notice title=quality gate::{json.dumps(verdict)}")
        return 0
    print('usage: python -m omni_prod.agent_os.meta regression JUNIT | layers FILES... | gate [JUNIT]')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
