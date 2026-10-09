"""Platform Capability Auditor (agent 47): computes every agent's and skill's
status from code, configuration and evidence -- never from a contract.

  BLOCKED          a named external blocker (credential, contract, account)
  NOT_IMPLEMENTED  no implementation, or it does not import
  NOT_CONFIGURED   implementation exists, required configuration not observed
  LIVE             implementation + FRESH live evidence (a real run on the
                   deployed system whose implementation files are unchanged
                   since the commit that ran -- digests in the evidence lock)
  PARTIAL          implementation + only unit evidence, or live evidence that
                   went stale because the code changed since

`python -m omni_prod.agent_os.audit --write` refreshes the evidence lock and
writes AGENT_OS_REGISTRY.json, docs/AGENT_OS_REGISTRY.md and the platform
matrices; CI checks they are current (no registry inflation can be committed).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from ..registry_audit import _importable, freshness, implementation_files, load_lock, refresh_lock
from .agents import AGENTS, GAPS
from .contracts import BLOCKED, LIVE, NOT_CONFIGURED, NOT_IMPLEMENTED, PARTIAL
from .evidence import AT
from .skills import SKILLS

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_JSON = ROOT / 'AGENT_OS_REGISTRY.json'
REGISTRY_MD = ROOT / 'docs' / 'AGENT_OS_REGISTRY.md'
OBSERVED_CONFIG = {
    # names observed on the build worker (deploy-worker notices); values never read
    'GEMINI_API_KEY', 'OMNI_MODEL_CATALOG_JSON', 'OMNI_SANDBOX_RUNNER_URL', 'OMNI_DATABASE_URL', 'OMNI_REDIS_URL',
    'OMNI_S3_ENDPOINT', 'OMNI_S3_BUCKET', 'OMNI_PREVIEW_DATA_ROOT',
}


def status_of(record, lock) -> dict:
    impl = tuple(record.implementation_location)
    if record.blocked_by:
        return {'status': BLOCKED, 'why': record.blocked_by, 'last_verified_at': None, 'last_verified_commit': None}
    if not impl or not all(_importable(t) for t in impl):
        missing = [t for t in impl if not _importable(t)]
        return {'status': NOT_IMPLEMENTED, 'why': ('does not import: ' + ', '.join(missing)) if missing else 'no implementation',
                'last_verified_at': None, 'last_verified_commit': None}
    if record.config and not all(c in OBSERVED_CONFIG for c in record.config):
        return {'status': NOT_CONFIGURED, 'why': 'not observed on the worker: ' + ', '.join(c for c in record.config if c not in OBSERVED_CONFIG),
                'last_verified_at': None, 'last_verified_commit': None}
    files = implementation_files(impl)
    fresh, stale = [], []
    for ev in record.evidence:
        if ev.kind != 'live':
            continue
        state, changed = freshness(ev, files, lock)
        (fresh if state == 'fresh' else stale).append((ev, changed))
    if fresh:
        ev = fresh[0][0]
        return {'status': LIVE, 'why': 'verified for: ' + '; '.join(dict.fromkeys(a for e, _ in fresh for a in e.asserts))[:400],
                'evidence': [e.ref for e, _ in fresh], 'last_verified_at': AT.get(ev.ref), 'last_verified_commit': ev.commit}
    if stale:
        changed = sorted({c for _, ch in stale for c in ch})
        return {'status': PARTIAL, 'why': 'live evidence is stale; code changed since: ' + (', '.join(changed) or 'unknown'),
                'evidence': [e.ref for e, _ in stale], 'last_verified_at': AT.get(stale[-1][0].ref),
                'last_verified_commit': stale[-1][0].commit}
    units = [e.ref for e in record.evidence if e.kind == 'unit']
    return {'status': PARTIAL, 'why': 'unit tests only' if units else 'code exists; no evidence',
            'evidence': units, 'last_verified_at': None, 'last_verified_commit': None}


def evidence_pairs() -> set[tuple[str, str]]:
    pairs = set()
    for rec in (*AGENTS, *SKILLS):
        for ev in rec.evidence:
            if ev.kind == 'live' and ev.commit and rec.implementation_location:
                pairs |= {(ev.commit, f) for f in implementation_files(rec.implementation_location)}
    return pairs


def audit(lock=None) -> dict:
    lock = load_lock() if lock is None else lock
    agents = []
    for a in AGENTS:
        st = status_of(a, lock)
        agents.append({'agent_key': a.agent_key, 'name': a.name, 'category': a.category, 'verifier': a.verifier,
                       'allowed_skills': list(a.allowed_skills), 'implementation_location': list(a.implementation_location),
                       'gap': GAPS.get(a.agent_key, ''), 'missing_contract_fields': a.missing_fields(), **st})
    skills = []
    for s in SKILLS:
        st = status_of(s, lock)
        skills.append({'skill_key': s.skill_key, 'category': s.category, 'primary_agent': s.primary_agent,
                       'verifier_agent': s.verifier_agent, 'implementation_location': list(s.implementation_location),
                       'gap': s.gap, 'missing_contract_fields': s.missing_fields(), **st})

    def counts(rows):
        out = {k: 0 for k in (LIVE, PARTIAL, NOT_CONFIGURED, NOT_IMPLEMENTED, BLOCKED)}
        for r in rows:
            out[r['status']] += 1
        return out
    return {'agents': agents, 'skills': skills,
            'summary': {'agents_total': len(agents), 'agents': counts(agents),
                        'skills_total': len(skills), 'skills': counts(skills)}}


def skill_statuses() -> dict:
    return {r['skill_key']: r['status'] for r in audit()['skills']}


def inflation_findings(result: dict) -> list[str]:
    """Claims the auditor refuses: LIVE without live evidence, contracts with
    empty required fields, verifiers that do not exist, an agent verifying itself."""
    keys = {a['agent_key'] for a in result['agents']} | {'requirements_traceability', 'privacy_reviewer', 'customer_success'}
    out = []
    for r in result['agents'] + result['skills']:
        name = r.get('agent_key') or r.get('skill_key')
        if r['status'] == LIVE and not r.get('evidence'):
            out.append(f'{name}: LIVE without evidence')
        if r['missing_contract_fields']:
            out.append(f"{name}: contract fields empty: {', '.join(r['missing_contract_fields'])}")
    for a in result['agents']:
        if a['verifier'] and a['verifier'] not in keys:
            out.append(f"{a['agent_key']}: unknown verifier {a['verifier']}")
        if a['verifier'] == a['agent_key']:
            out.append(f"{a['agent_key']}: verifies itself")
    return out


def markdown(result: dict) -> str:
    s = result['summary']
    lines = ['# Agent OS / Skills OS registry (computed)', '',
             '> Generated by `python -m omni_prod.agent_os.audit --write`. Status = code + configuration + fresh evidence;',
             '> LIVE only with a real run on the deployed system whose code is unchanged since. Do not edit by hand.', '',
             f"Agents: {s['agents_total']} — " + ', '.join(f'{k} {v}' for k, v in s['agents'].items()),
             f"Skills: {s['skills_total']} — " + ', '.join(f'{k} {v}' for k, v in s['skills'].items()), '',
             '## Agents', '', '| Agent | Category | Status | Verifier | Why / evidence | Gap |', '|---|---|---|---|---|---|']
    for a in result['agents']:
        lines.append(f"| {a['name']} (`{a['agent_key']}`) | {a['category']} | **{a['status']}** | {a['verifier'] or 'founder'} | "
                     f"{a['why'][:180]}{(' — ' + ', '.join(a.get('evidence') or [])[:120]) if a.get('evidence') else ''} | {a['gap']} |")
    lines += ['', '## Skills', '', '| Skill | Category | Status | Primary agent | Why | Gap |', '|---|---|---|---|---|---|']
    for k in result['skills']:
        lines.append(f"| `{k['skill_key']}` | {k['category']} | **{k['status']}** | {k['primary_agent']} | {k['why'][:140]} | {k['gap']} |")
    return '\n'.join(lines) + '\n'


def write(result: dict) -> None:
    REGISTRY_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str) + '\n', encoding='utf-8')
    REGISTRY_MD.write_text(markdown(result), encoding='utf-8')
    from .meta import write_matrices
    write_matrices(result)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if '--write' in argv:
        lock = refresh_lock(evidence_pairs())
        result = audit(lock)
        write(result)
    else:
        result = audit()
    problems = inflation_findings(result)
    print(json.dumps(result['summary']))
    for p in problems:
        print('INFLATION', p)
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
