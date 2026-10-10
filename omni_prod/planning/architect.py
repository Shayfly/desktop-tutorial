"""Chief Architect (Wave A §6, Unified Conversation OS §4).

Consumes the validated `intake-requirements/1` contract and produces an
`architecture-plan/1`: architecture, stack, capability dependencies, agents,
skills, providers, infrastructure, security boundaries, data model, API
contracts, UI architecture, testing strategy, acceptance criteria, budget,
risks, capability gaps, milestones and the execution DAG.

The plan is DETERMINISTIC (rules over the contract and the registries): it
costs nothing, so it can be kept up to date on every conversation turn
(provisional) and re-derived identically later. A model may review it for
complex products (task class `architecture`, floor 85); it never replaces the
validation. Each DAG task is bound to a `stage` of the existing build engine
(`worker_tasks._run_live_build_job`), the only engine that executes plans;
families without an engine produce a plan whose tasks are marked
non-executable and a feasibility verdict that blocks approval.
"""
from __future__ import annotations

import re
from decimal import Decimal

from ..agent_os.departments import department_of
from ..intake.families import EXECUTABLE
from . import feasibility as F
from .graph import ExecutionGraph, PlanTask
from .router import AgentSkillRouter

SCHEMA = 'architecture-plan/1'
D = Decimal


def _t(task_id, task_type, agent, skills, deps, stage, *, outputs, accept, verify, model_task=None, est='0', cap='0',
       iterations=1, conditional=False, tools=(), caps=(), complexity='medium', failure='block_dependents',
       executable=True, gap=''):
    return PlanTask(
        task_id=task_id, task_type=task_type, department=department_of(agent) or 'UNASSIGNED', responsible_agent=agent,
        required_skills=tuple(skills), required_tools=tuple(tools), required_capabilities=tuple(caps),
        dependencies=tuple(deps), inputs=tuple(f'output of {d}' for d in deps) or ('approved requirements contract',),
        expected_outputs=tuple(outputs), acceptance_criteria=tuple(accept), verification_strategy=verify,
        complexity=complexity, estimated_cost_usd=D(est), maximum_authorized_cost_usd=D(cap),
        retry_policy='bounded by the build repair rounds' if model_task else 'deterministic: rerun once on infrastructure error',
        timeout_policy='model call <= 300 s; sandbox <= 200 s; job <= 25 min',
        failure_policy=failure, rollback_policy='keep the best verified candidate (round snapshots)',
        escalation_policy='build FAILED with the exact failing check shown to the customer',
        stage=stage, model_task=model_task, max_iterations=iterations, conditional=conditional,
        executable=executable, gap=gap)


def web_graph(contract, *, budget_usd: D) -> ExecutionGraph:
    """The executable web plan: every task maps to a real stage of the existing engine."""
    complex_ = contract.complexity == 'complex'
    tasks = [
        _t('T01', 'requirements', 'requirements_agent', ('requirement_extraction', 'acceptance_criteria_generation'), (),
           'intake', outputs=('approved brief + requirements contract',), accept=('customer approval bound to the brief fingerprint',),
           verify='contract schema validation + server-bound approval', complexity='low'),
        _t('T02', 'plan_and_quote', 'product_planner', ('build_plan_generation', 'cost_estimation', 'capability_closure'), ('T01',),
           'planning', outputs=('build contract', 'reserved quote'), accept=('quote reserved before any model call',),
           verify='durable reservation row', complexity='low'),
        _t('T03', 'architecture', 'architecture_agent', ('data_model_design', 'api_contract_design'), ('T02',), 'architecture',
           outputs=('product spec: modules, data model, routes, acceptance tests',), accept=('spec covers every acceptance criterion',),
           verify='spec validation; later stages test against it', model_task='architecture', est='0.01', cap='0.05',
           complexity='high' if complex_ else 'medium'),
        _t('T04', 'implementation', 'coding_agent', ('file_create',), ('T03',), 'codegen',
           outputs=('repository files (frontend + backend + data)',), accept=('consistency gate: syntax, imports, routes, static refs',),
           verify='consistency gate + sandbox build (independent of the author)', model_task='codegen', est='0.06', cap='0.20',
           tools=('model router', 'repository writer'), complexity='high'),
        _t('T05', 'unit_tests', 'qa_agent', ('unit_test_execution',), ('T04',), 'unit_tests',
           outputs=('test results in the isolated sandbox',), accept=('all tests pass; no-op verify commands rejected',),
           verify='remote sandbox (no network); tests written by the author are not independent evidence',
           tools=('remote sandbox runner',), complexity='low'),
        _t('T06', 'repair', 'repair_agent', ('minimal_patch_generation', 'repair_execution'), ('T04',), 'repair',
           outputs=('minimal patch for the failing checks',), accept=('progress ranking improves or the best candidate is kept',),
           verify='rerun of the failing checks; worse repairs are rolled back', model_task='repair', est='0.02', cap='0.04',
           iterations=5, conditional=True, failure='continue_advisory'),
        _t('T07', 'preview_smoke', 'deployment_agent', ('preview_deploy', 'preview_health_check'), ('T05',), 'preview',
           outputs=('running preview of the candidate',), accept=('"/" serves the product (not a stub)',),
           verify='preview smoke test', tools=('preview runtime',), complexity='low'),
        _t('T08', 'behavioural_acceptance', 'behavioral_acceptance_agent', ('behavioral_acceptance_test', 'api_test'), ('T07',),
           'behavior', outputs=('acceptance results per criterion',), accept=('every acceptance ID covered and passing',),
           verify='HTTP behaviour tests derived from the approved acceptance criteria', tools=('preview runtime',)),
        _t('T09', 'browser_flow', 'browser_rehearsal_agent', ('browser_launch', 'form_test', 'javascript_error_detection'), ('T07',),
           'browser', outputs=('browser flow result',), accept=('main flow works in Chromium; no JS errors',),
           verify='real Chromium in the browser sandbox', tools=('browser sandbox',)),
        _t('T10', 'visual_qa', 'accessibility_agent', ('label_test', 'contrast_test'), ('T07',), 'visual',
           outputs=('desktop + mobile screenshots and findings',), accept=('no enforced layout rule fails',),
           verify='visual QA DOM audit at 1440x900 and 390x844', tools=('browser sandbox',)),
        _t('T11', 'security_scan', 'security_agent', ('secret_detection', 'security_release_gate'), ('T04',), 'security',
           outputs=('static security findings',), accept=('no blocking finding',), verify='static scan (platform-owned)',
           complexity='low'),
        _t('T12', 'release_gate', 'quality_gate_agent', ('release_gate', 'security_release_gate'),
           ('T08', 'T09', 'T10', 'T11'), 'quality_gate', outputs=('quality-report/1 decision',),
           accept=('every mandatory check PASS; NOT_RUN/UNKNOWN block',), verify='release policy (platform-owned, independent)',
           complexity='low'),
        _t('T13', 'version_release', 'release_agent', ('version_create', 'release_gate'), ('T12',), 'release',
           outputs=('immutable version + preview',), accept=('version stored with checksum',), verify='version load + checksum',
           complexity='low'),
        _t('T14', 'cost_settlement', 'cost_economics_agent', ('actual_cost_calculation', 'credit_settlement'), ('T04',), 'cost',
           outputs=('settlement at metered usage',), accept=('ledger sum == settlement; unknown cost reported as exposure',),
           verify='attempt ledger reconciliation', failure='continue_advisory', complexity='low'),
    ]
    if complex_:
        tasks.insert(3, _t('T03R', 'architecture_review', 'code_review_agent', ('xss_check',), ('T03',), 'review',
                           outputs=('independent review of the spec',), accept=('no blocking finding',),
                           verify='different model than the author when available', model_task='review', est='0.01', cap='0.05'))
        tasks = [t if t.task_id != 'T04' else PlanTask(**{**t.__dict__, 'dependencies': ('T03', 'T03R')}) for t in tasks]
    return ExecutionGraph(tuple(tasks), budget_usd)


def _gap_graph(contract, budget_usd: D) -> ExecutionGraph:
    """A non-executable family: the plan is shown, nothing runs."""
    fam = contract.product_family
    agents = {'game': 'game_engineering_2d_agent', 'media': 'media_orchestrator', 'automation': 'automation_agent',
              'mobile_app': 'frontend_agent', 'ai_agent': 'integration_agent', 'api_integration': 'integration_agent',
              '3d_experience': 'media_orchestrator'}
    agent = agents.get(fam, 'frontend_agent')
    return ExecutionGraph((
        _t('T01', 'requirements', 'requirements_agent', ('requirement_extraction',), (), 'intake',
           outputs=('requirements contract',), accept=('contract valid',), verify='schema'),
        _t('T02', f'{fam}_build', agent, (), ('T01',), 'none', outputs=(f'{fam} product',),
           accept=('not available',), verify='no verified engine', executable=False,
           gap=f'no execution engine for {fam} in this release'),
    ), budget_usd)


def _entities(contract) -> list[str]:
    text = contract.project_goal + ' ' + ' '.join(r.text for r in contract.functional_requirements)
    found = []
    for he, en in (('תור', 'Appointment'), ('הזמנ', 'Booking'), ('לקוח', 'Customer'), ('מוצר', 'Product'),
                   ('משימ', 'Task'), ('ציוד', 'Item'), ('עובד', 'Employee'), ('הוצא', 'Expense'),
                   ('appointment', 'Appointment'), ('booking', 'Booking'), ('customer', 'Customer'), ('task', 'Task'),
                   ('equipment', 'Item'), ('order', 'Order'), ('expense', 'Expense'), ('product', 'Product')):
        if re.search(he, text, re.I) and en not in found:
            found.append(en)
    return found or ['Item']


class ChiefArchitect:
    def __init__(self, router: AgentSkillRouter | None = None):
        self.router = router or AgentSkillRouter()

    def plan(self, contract, *, budget_usd: D = D('0.50'), status: str = 'PROPOSED') -> dict:
        feas = F.assess(contract)
        fam = contract.product_family
        graph = web_graph(contract, budget_usd=budget_usd) if fam in EXECUTABLE else _gap_graph(contract, budget_usd)
        from . import registry_view as R
        problems = graph.problems(agents=R.allowed_skills() if R.snapshot()['loaded'] else None,
                                  skills=R.skill_keys() if R.snapshot()['loaded'] else None)
        assignments = [self.router.assign(t) for t in graph.tasks]
        entities = _entities(contract)
        auth = contract.authentication_requirements['mode']
        plan = {
            'schema': SCHEMA, 'status': status, 'brief_fingerprint': contract.brief_fingerprint,
            'requirements_fingerprint': contract.fingerprint(), 'product_family': fam, 'complexity': contract.complexity,
            'architecture': ('single web application: server-rendered pages + JSON API + embedded database, '
                             'one repository, preview runtime') if fam in EXECUTABLE else f'{fam}: not executable in this release',
            'technical_stack': {'server': 'Python (FastAPI/Flask per dependency allowlist)', 'storage': 'SQLite in the preview volume',
                                'ui': 'HTML/CSS/JS with design tokens from the brief', 'tests': 'pytest in the isolated sandbox'}
            if fam in EXECUTABLE else {},
            'data_model': [{'entity': e, 'fields': 'derived during architecture (T03)'} for e in entities],
            'api_contracts': [{'method': m, 'path': f'/api/{e.lower()}s{s}'} for e in entities
                              for m, s in (('GET', ''), ('POST', ''), ('PUT', '/{id}'), ('DELETE', '/{id}'))],
            'ui_architecture': {'languages': contract.languages, 'direction': 'rtl' if 'he' in contract.languages else 'ltr',
                                'viewports': ['desktop 1440x900', 'mobile 390x844'], 'design': contract.design_preferences},
            'security_boundaries': [f'sign-in: {auth}', 'generated code runs only in the isolated sandbox / preview runtime',
                                    'previews private by default (owner token)'] +
                                   (['personal data visible only to authorized people'] if contract.data_requirements.get('personal_data') else []),
            'infrastructure': ['remote sandbox (no network)', 'preview runtime', 'artifact storage (R2)', 'PostgreSQL ledgers'],
            'capability_dependencies': sorted({c for t in graph.tasks for c in t.required_skills}),
            'agent_requirements': sorted({t.responsible_agent for t in graph.tasks}),
            'provider_requirements': sorted({a['model_candidates'][0] for a in assignments if a.get('model_candidates')}),
            'testing_strategy': ['consistency gate during generation', 'sandbox unit tests', 'behavioural acceptance per criterion',
                                 'browser flow', 'visual QA desktop + mobile', 'static security scan', 'release policy'],
            'acceptance_criteria': contract.acceptance_criteria,
            'budget': {'graph_authorized_usd': str(graph.authorized_total()) if graph.authorized_total() is not None else None,
                       'budget_usd': str(budget_usd),
                       'note': 'planning estimate; the durable build reservation is authoritative'},
            'risks': [f.reason for f in feas.findings if f.outcome != F.FEASIBLE][:10],
            'capability_gaps': [f.to_dict() for f in feas.findings if f.outcome in (F.BLOCKED, F.UNSUPPORTED)],
            'milestones': ['requirements approved', 'code generated', 'tests pass', 'preview verified', 'version released'],
            'feasibility': feas.to_dict(),
            'execution_graph': graph.to_dict(),
            'graph_fingerprint': graph.fingerprint(),
            'graph_problems': problems,
            'layers': graph.layers() if not any('cycle' in p for p in problems) else [],
            'critical_path': graph.critical_path() if not problems else [],
            'assignments': assignments,
            'executable': feas.buildable and not problems and all(t.executable for t in graph.tasks),
        }
        return plan
