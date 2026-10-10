"""Truth matrix (Production Assurance v2 §3, issue #6 Phase A).

Requirement -> Capability -> Agent -> Skill -> Implementation -> Provider ->
Tests -> Evidence -> Cost -> Status, for the customer's critical path first.

Status of a row = the WEAKEST status among its skills/platform capabilities,
computed by the capability auditor (code + configuration + fresh evidence);
nothing here is typed by hand except the mapping. `shown_to_customer` marks
what the UI presents as available: such a row below REAL_SERVER_VERIFIED is a
finding (§3 acceptance condition).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..runtime_bindings import Evidence
from .contracts import (BLOCKED, IMPLEMENTED, INTEGRATION_TESTED, LIVE, NOT_IMPLEMENTED, REAL_SERVER_VERIFIED,
                        UNIT_TESTED)
from .evidence import FREE, GATE_REPLAY, PAID

ROOT = Path(__file__).resolve().parents[2]
TRUTH_JSON = ROOT / 'TRUTH_MATRIX.json'
TRUTH_MD = ROOT / 'docs' / 'TRUTH_MATRIX.md'
RANK = {NOT_IMPLEMENTED: 0, BLOCKED: 0, IMPLEMENTED: 1, UNIT_TESTED: 2, INTEGRATION_TESTED: 3,
        REAL_SERVER_VERIFIED: 4, LIVE: 5}


@dataclass(frozen=True)
class PlatformCapability:
    """A platform capability that is not one of the 427 product skills."""
    key: str
    implementation_location: tuple[str, ...]
    evidence: tuple = ()
    blocked_by: str = ''
    config: tuple = ()


U = lambda path: Evidence('unit', path)  # noqa: E731

PLATFORM = {c.key: c for c in (
    PlatformCapability('platform_accounts', ('omni_prod.creator_accounts:PostgresAccountService',
                                             'omni_prod.identity_lifecycle:IdentityService'),
                       (FREE, U('tests/test_m5_identity_lifecycle.py'))),
    PlatformCapability('contract_bound_approval', ('omni_prod.job_repository:PostgresBuildRepository.claim_contract_build',),
                       (PAID,)),
    PlatformCapability('consistency_gate', ('omni_prod.consistency_gate:ConsistencyGateExecutor',),
                       (GATE_REPLAY, U('tests/test_consistency_gate.py'))),
    PlatformCapability('release_policy', ('omni_prod.release_policy:build_report',), (U('tests/test_release_policy.py'),)),
    PlatformCapability('round_snapshots_rollback', ('omni_prod.worker_tasks:install_round_snapshots',),
                       (U('tests/test_repair_stop_loss.py'),)),
    PlatformCapability('zip_export', ('omni_prod.v26_platform:V26UniversalPlatform.export', 'omni_prod.unified_engine:UnifiedOmniEngine.export_zip'),
                       (U('tests/test_v25_unified_v10_parity.py'),)),
    PlatformCapability('version_rollback', ('omni_prod.modification_repository:PostgresModificationRepository.rollback',),
                       (U('tests/test_m4_acceptance.py'),)),
    PlatformCapability('publish', (), blocked_by=''),
    PlatformCapability('invoice_reconciliation', ('omni_prod.qa_budget:qa_used_usd',),
                       blocked_by='needs the provider billing export (founder access to Google AI Studio / Cloud billing)'),
    PlatformCapability('second_model_provider', ('omni_prod.routed_gateway:RoutedModelGateway',),
                       blocked_by='OpenAI: no credits (HTTP 429); Anthropic: credit balance too low (HTTP 400)'),
    PlatformCapability('visual_qa_desktop_mobile', ('omni_prod.visual_qa:VisualQAExecutor',),
                       (Evidence('integration', 'tests/test_visual_qa.py'),)),
    PlatformCapability('write_ahead_cost_ledger', ('omni_prod.attempt_ledger:persist_attempts',
                                                   'omni_prod.worker_tasks:prior_worker_metered_cost'),
                       (Evidence('integration', 'tests/test_actual_cost_settlement.py'),)),
    PlatformCapability('unit_economics_report', ('omni_prod.economics_report:compute',),
                       (U('tests/test_economics_report.py'),)),
    PlatformCapability('durable_stage_evidence', ('omni_prod.release_policy:persist',),
                       (Evidence('integration', 'tests/test_release_policy.py'),)),
    PlatformCapability('performance_budgets', ()),
)}


@dataclass(frozen=True)
class Row:
    requirement: str
    capability: str
    agent: str
    skills: tuple[str, ...] = ()
    platform: tuple[str, ...] = ()
    provider: str = 'none (deterministic)'
    tests: tuple[str, ...] = ()
    cost: str = '$0'
    shown_to_customer: bool = False
    note: str = ''


ROWS = (
    Row('Describe the product in natural language (Hebrew/English)', 'discovery', 'discovery_agent',
        ('requirement_extraction', 'acceptance_criteria_generation'), tests=('tests/test_brief_capability_detection.py',),
        shown_to_customer=True),
    Row('Clarifying questions only when needed', 'discovery questions', 'discovery_agent',
        ('smart_question_generation', 'safe_default_selection'), shown_to_customer=True),
    Row('Plan and cost quote before the build', 'plan + quote', 'product_planner',
        ('build_plan_generation', 'build_quote'), shown_to_customer=True),
    Row('Approval binds the build to the approved contract', 'server-side approval', 'executive_orchestrator',
        platform=('contract_bound_approval',), shown_to_customer=True),
    Row('Sign up / sign in to 148AI', '148AI accounts', 'security_agent', platform=('platform_accounts',),
        tests=('tests/test_m5_identity_lifecycle.py',), shown_to_customer=True),
    Row('Generate the product code', 'code generation', 'coding_agent', ('file_create',), provider='Gemini (catalog)',
        cost='metered per call', shown_to_customer=True),
    Row('Detect cross-file errors before running (syntax, imports, routes, assets)', 'consistency gate', 'qa_agent',
        platform=('consistency_gate',), tests=('tests/test_consistency_gate.py',)),
    Row('Run the product\'s tests in an isolated sandbox', 'sandbox verification', 'qa_agent', ('unit_test_execution',),
        provider='sandbox runner (no network)', cost='$0 marginal', note='tests are written by the generating model'),
    Row('Repair focused on real errors; worse repairs rolled back', 'repair loop', 'repair_agent',
        ('repair_execution', 'retry_decision'), platform=('round_snapshots_rollback',), provider='Gemini',
        tests=('tests/test_repair_stop_loss.py',), cost='metered per call'),
    Row('The product starts for preview', 'preview smoke', 'deployment_agent', ('page_load_test',)),
    Row('The product does what was asked (behaviour over HTTP)', 'behavioural acceptance', 'behavioral_acceptance_agent',
        ('behavioral_acceptance_test',), note='steps written by the model; platform enforces required kinds'),
    Row('A real browser uses the product (forms, JS errors)', 'browser check', 'browser_rehearsal_agent',
        ('browser_acceptance_test', 'javascript_error_detection')),
    Row('Looks right on desktop and mobile, RTL', 'visual QA', 'ux_ui_design_agent',
        ('mobile_view_test', 'desktop_view_test', 'responsive_test'), platform=('visual_qa_desktop_mobile',),
        note='shadow mode: measured and recorded, not yet blocking'),
    Row('Accessible (labels, contrast, keyboard)', 'accessibility', 'accessibility_agent', ('label_test', 'contrast_test')),
    Row('Performance within budget', 'performance', 'performance_agent', platform=('performance_budgets',)),
    Row('No secrets or unsafe code in the product', 'security scan', 'security_agent',
        ('secret_detection', 'security_release_gate')),
    Row('Never READY when a mandatory check failed or did not run', 'release policy', 'quality_gate_agent',
        platform=('release_policy',), tests=('tests/test_release_policy.py', 'tests/test_release_blocks_on_failed_acceptance.py')),
    Row('Private preview; sharing only on purpose', 'preview access', 'deployment_agent',
        ('preview_access_protect', 'preview_token_revoke'), shown_to_customer=True),
    Row('Preview data survives restarts and new versions', 'preview data', 'database_agent', ('persistence_test',),
        shown_to_customer=True),
    Row('Change the product in natural language', 'modification', 'product_evolution_agent', ('file_modify',),
        provider='Gemini', cost='metered per call', shown_to_customer=True),
    Row('Version history and rollback', 'versions', 'release_agent', ('version_create',),
        platform=('version_rollback',), shown_to_customer=True),
    Row('Download the product as ZIP', 'export', 'release_agent', platform=('zip_export',), shown_to_customer=True),
    Row('Publish to a live address', 'publish', 'deployment_agent', ('release_publish',), platform=('publish',),
        note='refused with 501; not shown in the UI'),
    Row('Stop a build; live progress journal', 'cancel + journal', 'infrastructure_agent', ('job_cancel',),
        shown_to_customer=True),
    Row('Recover a build after a worker crash', 'crash recovery', 'infrastructure_agent', ('job_resume', 'stale_job_recovery')),
    Row('Charge only actual usage (metered settlement)', 'settlement', 'cost_economics_agent',
        ('credit_reservation', 'actual_cost_calculation', 'credit_settlement'), platform=('write_ahead_cost_ledger',),
        cost='ledger'),
    Row('Cost per build / per successful build / by model, from the ledger', 'unit economics', 'cost_economics_agent',
        ('margin_calculation',), platform=('unit_economics_report',)),
    Row('Every check stored per build, bound to the artifact', 'stage evidence', 'quality_gate_agent',
        platform=('durable_stage_evidence',)),
    Row('Hard budget ceiling per build and in total', 'budget guard', 'cost_economics_agent', ('budget_guard',)),
    Row('Costs reconciled with provider invoices', 'reconciliation', 'cost_economics_agent',
        platform=('invoice_reconciliation',)),
    Row('Backups that restore', 'backup/restore', 'backup_recovery_agent', ('restore_verification',)),
    Row('Fallback to a second AI provider', 'provider fallback', 'provider_router_agent',
        ('provider_fallback_selection',), platform=('second_model_provider',)),
    Row('Sign-in and roles inside generated products', 'generated-app auth', 'identity_auth_agent', ('signup', 'login')),
    Row('Images for the product', 'media', 'image_agent', ('text_to_image',)),
    Row('Automations', 'automation', 'automation_agent', ('workflow_test',)),
    Row('2D games', 'games', 'game_engineering_2d_agent', ('gameplay_test',)),
)


def build(result: dict, lock) -> dict:
    from .audit import status_of
    skills = {s['skill_key']: s for s in result['skills']}
    rows, findings = [], []
    for row in ROWS:
        parts = []
        for k in row.skills:
            s = skills.get(k)
            parts.append((f'skill:{k}', s['status'] if s else NOT_IMPLEMENTED, (s or {}).get('evidence') or [],
                          (s or {}).get('implementation_location') or [], (s or {}).get('why', 'unknown skill')))
        for k in row.platform:
            cap = PLATFORM[k]
            st = status_of(cap, lock)
            parts.append((f'platform:{k}', st['status'], st.get('evidence') or [], list(cap.implementation_location), st['why']))
        status = min((p[1] for p in parts), key=lambda s: (RANK[s], s != BLOCKED)) if parts else NOT_IMPLEMENTED
        entry = {'requirement': row.requirement, 'capability': row.capability, 'agent': row.agent,
                 'skills': list(row.skills), 'platform': list(row.platform),
                 'implementation': sorted({i for p in parts for i in p[3]}), 'provider': row.provider,
                 'tests': [t for t in row.tests if (ROOT / t).exists()], 'evidence': sorted({e for p in parts for e in p[2]}),
                 'cost': row.cost, 'status': status, 'shown_to_customer': row.shown_to_customer, 'note': row.note,
                 'parts': [{'part': p[0], 'status': p[1], 'why': p[4][:200]} for p in parts]}
        rows.append(entry)
        if row.shown_to_customer and RANK[status] < RANK[REAL_SERVER_VERIFIED]:
            findings.append(f"shown to the customer but {status}: {row.requirement}")
    counts = {}
    for r in rows:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    return {'rows': rows, 'counts': counts, 'customer_visible_findings': findings}


def markdown(matrix: dict) -> str:
    lines = ['# Truth matrix (computed)', '',
             '> Generated by `python -m omni_prod.agent_os.audit --write`. Row status = weakest part; '
             'REAL_SERVER_VERIFIED = fresh run on pre-staging; LIVE = production (none yet). Do not edit by hand.', '',
             'Counts: ' + ', '.join(f'{k} {v}' for k, v in sorted(matrix['counts'].items())), '']
    if matrix['customer_visible_findings']:
        lines += ['## Shown to the customer without real-server evidence', ''] + \
                 [f'- {f}' for f in matrix['customer_visible_findings']] + ['']
    lines += ['| Requirement | Agent | Skills / platform | Status | Shown | Evidence | Cost | Note |', '|---|---|---|---|---|---|---|---|']
    for r in matrix['rows']:
        parts = '; '.join(f"{p['part']}={p['status']}" for p in r['parts'])
        lines.append(f"| {r['requirement']} | {r['agent']} | {parts} | **{r['status']}** | {'yes' if r['shown_to_customer'] else ''} | "
                     f"{', '.join(r['evidence'])[:120]} | {r['cost']} | {r['note']} |")
    return '\n'.join(lines) + '\n'


def write(result: dict, lock) -> dict:
    matrix = build(result, lock)
    TRUTH_JSON.write_text(json.dumps(matrix, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    TRUTH_MD.write_text(markdown(matrix), encoding='utf-8')
    return matrix
