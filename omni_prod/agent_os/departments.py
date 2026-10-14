"""The 18 departments of the 148AI software company (Wave A §7).

Every registered agent belongs to exactly one department. A department's
readiness is COMPUTED from its agents' audited statuses (AGENT_OS_REGISTRY),
never declared:

  READY            every core agent REAL_SERVER_VERIFIED and no missing role
  PARTIAL          at least one core agent verified, something is not
  IMPLEMENTED      code exists for core agents, nothing verified on the real server
  BLOCKED          core agents exist but are blocked by a named external dependency
  NOT_IMPLEMENTED  no core agent has an implementation

    python -m omni_prod.agent_os.departments --write   # DEPARTMENT_MATRIX.json + docs/DEPARTMENT_MATRIX.md
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JSON_OUT = ROOT / 'DEPARTMENT_MATRIX.json'
MD_OUT = ROOT / 'docs' / 'DEPARTMENT_MATRIX.md'


@dataclass(frozen=True)
class Department:
    key: str
    name: str
    responsibilities: str
    core_agents: tuple[str, ...]
    support_agents: tuple[str, ...]
    missing_roles: tuple[str, ...]
    missing_adapters: tuple[str, ...]
    forbidden: str
    hands_off_to: tuple[str, ...]
    outputs: str
    verification: str
    cost_policy: str


_NO_SELF = 'never verifies its own output; never spends outside the build reservation'
DEPARTMENTS: tuple[Department, ...] = (
    Department('D01', 'Customer Discovery & Product Requirements', 'intake conversation, requirements, ambiguity, approval',
               ('intake_agent', 'discovery_agent', 'requirements_agent'), (), (),
               (), 'never approves for the customer; never starts a paid build', ('D02', 'D03'),
               'versioned brief + intake-requirements/1 contract', 'contract schema validation; customer approval bound to the brief fingerprint',
               'deterministic by default ($0); model interpretation only within the conversation budget'),
    Department('D02', 'Product Management & Planning', 'scope, milestones, prioritisation, delivery constraints',
               ('product_planner', 'executive_orchestrator'), ('product_evolution_agent',), ('backlog_manager',), (),
               'never changes approved scope without a new approval', ('D03',), 'build plan + quote',
               'plan bound to the approved brief; quote reserved before work', 'planning is deterministic ($0)'),
    Department('D03', 'Systems Architecture', 'architecture, decisions, dependency graph, contracts',
               ('chief_architect', 'architecture_agent'), (), (), (), 'never assigns work to unimplemented agents as executable',
               ('D05', 'D06', 'D07', 'D08'), 'architecture plan + validated execution DAG',
               'DAG validation (cycles, closure, budget); feasibility gate', 'architecture model routed at quality floor 85'),
    Department('D04', 'UX Research & Product Design', 'user flows, usability, accessibility',
               ('accessibility_agent',), (), ('ux_research_agent',), (), 'never ships a flow without a browser check',
               ('D05',), 'flows, accessibility findings', 'visual QA accessibility rules (advisory until founder decision)', '$0 (deterministic checks)'),
    Department('D05', 'UI & Design Systems', 'responsive UI, components, RTL/LTR',
               ('ux_ui_design_agent', 'localization_rtl_agent'), (), (), (), 'never hard-codes colours outside the design tokens',
               ('D06',), 'design tokens from the brief', 'visual QA layout rules desktop + mobile', 'inside the codegen call'),
    Department('D06', 'Frontend Engineering', 'pages, state, routing, client tests',
               ('frontend_agent', 'coding_agent'), ('seo_web_quality_agent',), (), (), _NO_SELF, ('D12',),
               'UI files in the repository', 'consistency gate, browser flow, visual QA', 'codegen floor 85, within the reservation'),
    Department('D07', 'Backend & API Engineering', 'services, business logic, API contracts, auth',
               ('backend_agent',), ('identity_auth_agent',), (), ('generated-app identity provider',), _NO_SELF, ('D12',),
               'API files', 'sandbox tests, behavioural acceptance via HTTP', 'inside the codegen call'),
    Department('D08', 'Database & Data Engineering', 'schemas, persistence, integrity, migrations',
               ('database_agent',), ('migration_agent', 'analytics_agent'), (), (), _NO_SELF, ('D07',),
               'schema + persistence', 'persistence across restart (preview data checks)', 'inside the codegen call'),
    Department('D09', 'Integrations & Connectivity', 'external APIs, OAuth, webhooks, payments',
               ('integration_agent',), (), ('payments_agent', 'messaging_agent'),
               ('payments adapter', 'email/SMS adapter', 'OAuth connector'), 'never stores raw secrets; references only',
               ('D07',), 'connectors', 'contract tests + live credential checks', 'per-integration quote (none connected)'),
    Department('D10', 'DevOps, Cloud & Infrastructure', 'workers, sandboxes, previews, backups',
               ('infrastructure_agent', 'deployment_agent'), ('backup_recovery_agent',), (), (),
               'never exposes the host Docker socket publicly', ('D17',), 'running previews, healthy workers',
               'deploy probes, preview data self-test', 'free-tier infrastructure; no per-build allocation yet'),
    Department('D11', 'Security, Privacy & Compliance', 'threats, permissions, secrets, IP',
               ('security_agent', 'compliance_ip_agent'), (), ('privacy_reviewer',), (),
               'never certifies code it wrote', ('D17',), 'security findings, rights assessment',
               'static scan + preview access checks', '$0 (deterministic)'),
    Department('D12', 'QA & Test Engineering', 'unit, integration, E2E, browser, regression',
               ('qa_agent', 'behavioral_acceptance_agent', 'browser_rehearsal_agent', 'code_review_agent'),
               ('repair_agent', 'performance_agent', 'regression_guardian', 'golden_path_verifier', 'system_test_orchestrator'),
               (), ('load-test runner',), 'tests written by the coding agent are not independent evidence', ('D17',),
               'test results, repairs', 'release policy mandatory checks', 'repair bounded by rounds and budget'),
    Department('D13', 'AI & Model Engineering', 'model routing, evaluations, inference economics',
               ('provider_router_agent',), ('failure_injection_agent',), ('model_evaluation_agent',), (),
               'never routes below a task\'s mandatory quality floor', ('D18',), 'routing decisions, provider health',
               'provider matrix validation, circuit-breaker tests', 'cost per verified success, not token price'),
    Department('D14', 'Game Development', 'engines, gameplay, physics, saves, multiplayer',
               ('game_designer_2d_agent', 'level_designer_2d_agent', 'game_engineering_2d_agent', 'game_qa_2d_agent'),
               (), ('multiplayer_engineer',), ('game engine runner', 'gameplay test harness'), 'never claims a playable game without a gameplay test',
               ('D12',), 'games (not yet)', 'gameplay tests (not implemented)', 'not priced'),
    Department('D15', 'Media & Creative Production', 'image, video, music, speech',
               ('media_orchestrator', 'image_agent', 'video_agent', 'voice_speech_agent', 'audio_music_agent'), (),
               ('3d_asset_agent',), ('image adapter on the worker', 'video adapter', 'TTS adapter', 'music adapter'),
               'never uses media without confirmed commercial rights', ('D06',), 'assets (not yet)',
               'artifact checks + rights metadata', 'per-asset quote; disabled until authorized'),
    Department('D16', 'Automation & Agent Engineering', 'workflows, triggers, tool-use agents',
               ('automation_agent',), (), ('workflow_runner',), ('scheduler/trigger runtime',),
               'never runs customer automations without a sandbox and budget', ('D12',), 'automations (not yet)',
               'workflow tests (not implemented)', 'not priced'),
    Department('D17', 'Release, Reliability & Operations', 'release gate, observability, incidents, rollback',
               ('release_agent', 'quality_gate_agent', 'observability_agent', 'sre_reliability_agent'),
               ('diagnostic_agent', 'platform_capability_auditor'), (), (),
               'never marks READY with a mandatory check FAIL/NOT_RUN/UNKNOWN', ('D18',), 'versions, quality reports',
               'release policy + stage evidence rows', '$0'),
    Department('D18', 'Commercial Economics & Customer Success', 'quotes, credits, settlement, unit economics, support',
               ('cost_economics_agent',), ('support_agent',), (), ('invoice reconciliation export',),
               'never treats an unknown cost as zero', (), 'quotes, settlements, economics report',
               'ledger = settlement; reconciliation blocked on billing export', 'reservation before work; settle at metered cost'),
)
BY_KEY = {d.key: d for d in DEPARTMENTS}


def department_of(agent_key: str) -> str | None:
    for d in DEPARTMENTS:
        if agent_key in d.core_agents or agent_key in d.support_agents:
            return d.key
    return None


def readiness(dep: Department, statuses: dict[str, str]) -> str:
    core = [statuses.get(a, 'NOT_IMPLEMENTED') for a in dep.core_agents]
    verified = [s in ('REAL_SERVER_VERIFIED', 'LIVE') for s in core]
    if all(verified) and not dep.missing_roles and not dep.missing_adapters:
        return 'READY'
    if any(verified):
        return 'PARTIAL'
    if all(s == 'NOT_IMPLEMENTED' for s in core):
        return 'NOT_IMPLEMENTED'
    if all(s in ('BLOCKED', 'NOT_IMPLEMENTED') for s in core):
        return 'BLOCKED'
    return 'IMPLEMENTED'


def build(registry: dict | None = None) -> dict:
    if registry is None:
        registry = json.loads((ROOT / 'AGENT_OS_REGISTRY.json').read_text(encoding='utf-8'))
    statuses = {a['agent_key']: a['status'] for a in registry['agents']}
    skills_by_agent: dict[str, list] = {}
    for s in registry['skills']:
        skills_by_agent.setdefault(s.get('primary_agent'), []).append(s)
    rows = []
    for d in DEPARTMENTS:
        agents = d.core_agents + d.support_agents
        sk = [s for a in agents for s in skills_by_agent.get(a, [])]
        counts: dict[str, int] = {}
        for s in sk:
            counts[s['status']] = counts.get(s['status'], 0) + 1
        rows.append({'key': d.key, 'name': d.name, 'readiness': readiness(d, statuses),
                     'responsibilities': d.responsibilities,
                     'core_agents': {a: statuses.get(a, 'NOT_REGISTERED') for a in d.core_agents},
                     'support_agents': {a: statuses.get(a, 'NOT_REGISTERED') for a in d.support_agents},
                     'skills': dict(sorted(counts.items())), 'missing_roles': list(d.missing_roles),
                     'missing_adapters': list(d.missing_adapters), 'forbidden': d.forbidden,
                     'hands_off_to': list(d.hands_off_to), 'outputs': d.outputs, 'verification': d.verification,
                     'cost_policy': d.cost_policy})
    unassigned = sorted(set(statuses) - {a for d in DEPARTMENTS for a in d.core_agents + d.support_agents})
    summary: dict[str, int] = {}
    for r in rows:
        summary[r['readiness']] = summary.get(r['readiness'], 0) + 1
    return {'schema': 'department-matrix/1', 'summary': dict(sorted(summary.items())), 'departments': rows,
            'unassigned_agents': unassigned}


def problems(m: dict, registry: dict | None = None) -> list[str]:
    out = []
    seen: dict[str, str] = {}
    for d in DEPARTMENTS:
        for a in d.core_agents + d.support_agents:
            if a in seen:
                out.append(f'{a} is in {seen[a]} and {d.key}')
            seen[a] = d.key
    if m['unassigned_agents']:
        out.append('agents without a department: ' + ', '.join(m['unassigned_agents']))
    for r in m['departments']:
        for a, st in {**r['core_agents'], **r['support_agents']}.items():
            if st == 'NOT_REGISTERED':
                out.append(f'{r["key"]}: {a} is not in the agent registry')
    return out


def markdown(m: dict) -> str:
    lines = ['# 18 departments — readiness (generated)', '',
             'Generated by `python -m omni_prod.agent_os.departments --write` from the audited agent registry. '
             'Readiness is computed from agent statuses; a department with many registered agents can still be PARTIAL.', '',
             f'Summary: {m["summary"]}', '',
             '| # | Department | Readiness | Core agents (status) | Missing roles / adapters |', '|---|---|---|---|---|']
    for r in m['departments']:
        core = ', '.join(f'{a} ({s})' for a, s in r['core_agents'].items())
        miss = ', '.join(r['missing_roles'] + r['missing_adapters']) or '—'
        lines.append(f'| {r["key"]} | {r["name"]} | **{r["readiness"]}** | {core} | {miss} |')
    return '\n'.join(lines) + '\n'


def render(m: dict) -> tuple[str, str]:
    return json.dumps(m, indent=1, ensure_ascii=False) + '\n', markdown(m)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='omni_prod.agent_os.departments')
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args(argv)
    m = build()
    probs = problems(m)
    if probs:
        print('\n'.join(probs))
        return 1
    js, md = render(m)
    if args.write:
        JSON_OUT.write_text(js, encoding='utf-8')
        MD_OUT.write_text(md, encoding='utf-8')
    print(json.dumps(m['summary']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
