"""Registry Auditor: computes what each agent role really is, deterministically.

Lifecycle (founder spec 2026-10-08, "distinguish at all times"):
  DEFINED      -- in the catalog only (a role, a prompt or a registry entry)
  IMPLEMENTED  -- real, importable code serves it
  CONNECTED    -- that code has its configuration/provider (names observed)
  VERIFIED     -- it worked in a real run with a recorded id
  BLOCKED      -- a named credential, permission or service is missing

The status comes from `runtime_bindings` plus checks run here (symbols import,
configuration observed or present in the given environment). Nothing becomes
VERIFIED without live evidence; the older registry's self-declared statuses are
reported where they disagree.

    python -m omni_prod.registry_audit            # markdown table to stdout
    python -m omni_prod.registry_audit --write    # docs/AGENT_SKILL_STATUS.md
"""
from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .agent_catalog import CATALOG, AgentRole
from .runtime_bindings import BY_ROLE, Binding

DEFINED, IMPLEMENTED, CONNECTED, VERIFIED, BLOCKED = 'DEFINED', 'IMPLEMENTED', 'CONNECTED', 'VERIFIED', 'BLOCKED'
ORDER = (VERIFIED, CONNECTED, IMPLEMENTED, BLOCKED, DEFINED)


@dataclass
class Row:
    role: AgentRole
    lifecycle: str
    implementation: str
    configuration: str
    verification: str
    evidence: str
    cost: str
    gap: str
    issues: list[str] = field(default_factory=list)


def _importable(target: str) -> bool:
    module, _, symbol = target.partition(':')
    try:
        obj = importlib.import_module(module)
    except Exception:
        return False
    for part in symbol.split('.') if symbol else ():
        if not hasattr(obj, part):
            return False
        obj = getattr(obj, part)
    return True


def _config_state(binding: Binding, env: Mapping[str, str]) -> tuple[bool, str]:
    missing, notes = [], []
    for req in binding.config:
        present = req.observed or all((env.get(n) or '').strip() for n in req.names)
        notes.append(f"{'/'.join(req.names)}: {'ok' if present else 'MISSING'}" + (f' ({req.observed})' if req.observed else ''))
        if not present:
            missing.extend(req.names)
    return (not missing), ('; '.join(notes) or 'none needed'),


def audit_role(role: AgentRole, env: Mapping[str, str] | None = None, registry_status: str | None = None) -> Row:
    env = os.environ if env is None else env
    binding = BY_ROLE.get(role.key)
    issues: list[str] = []
    if binding is None:
        lifecycle = DEFINED
        row = Row(role, lifecycle, '—', '—', 'not verified', '—', '—', 'not implemented')
    else:
        bad = [t for t in binding.implementation if not _importable(t)]
        if bad:
            issues.append('implementation does not import: ' + ', '.join(bad))
        configured, config_text = _config_state(binding, env)
        live = [e for e in binding.evidence if e.kind == 'live']
        unit = [e for e in binding.evidence if e.kind == 'unit']
        if bad:
            lifecycle = DEFINED
        elif binding.blocked_by:
            lifecycle = BLOCKED
        elif not configured:
            lifecycle = BLOCKED
        elif live:
            lifecycle = VERIFIED
        elif binding.config or unit:
            lifecycle = CONNECTED
        else:
            lifecycle = IMPLEMENTED
        verification = (f'live ({binding.scope})' if live else 'unit tests only' if unit else 'none')
        evidence = '; '.join(f'{e.ref}' + (f' — {e.note}' if e.note else '') for e in binding.evidence) or '—'
        row = Row(role, lifecycle, ', '.join(t.split(':')[1] or t for t in binding.implementation),
                  (binding.blocked_by + '; ' if binding.blocked_by else '') + config_text,
                  verification, evidence, binding.cost or '—', '; '.join(binding.gaps) or '—', issues)
    if registry_status in ('LIVE',) and row.lifecycle != VERIFIED:
        row.issues.append(f'older registry says {registry_status} but there is no live evidence')
    if registry_status in ('PARTIAL', 'LIVE') and row.lifecycle == DEFINED:
        row.issues.append(f'older registry says {registry_status} but no code on a runtime path serves this role')
    return row


def _registry_statuses() -> dict[str, str]:
    try:
        from .agents_registry import build_canonical_agents_registry
        from .skills_registry import build_canonical_skills_registry
        agents = build_canonical_agents_registry(build_canonical_skills_registry())
        return {a.key: a.status.value for a in agents.all()}
    except Exception:
        return {}


def skill_registry_findings() -> list[str]:
    """Older skills registry entries that claim more than the code delivers."""
    findings = []
    try:
        from .skills_registry import build_canonical_skills_registry
        skills = build_canonical_skills_registry().all()
    except Exception as exc:
        return [f'skills registry could not be built: {type(exc).__name__}']
    root = Path(__file__).resolve().parent.parent
    off_path = {}
    for s in skills:
        if s.implementation_location and not (root / s.implementation_location).exists():
            findings.append(f'{s.key}: implementation file {s.implementation_location} does not exist')
        if s.status.value in ('PARTIAL', 'LIVE') and not s.key.startswith(('skill.software.', 'skill.target.web', 'skill.target.saas', 'skill.internal.')):
            family = s.key.split('.')[1]
            off_path[family] = off_path.get(family, 0) + 1
    for family, n in sorted(off_path.items()):
        findings.append(f'{n} "{family}" skills are PARTIAL in the registry but none runs on a verified path '
                        f'(treat as DEFINED until a runtime binding with evidence exists)')
    if skills and all(s.last_verified_version == 'registry-governance-v1' for s in skills if s.last_verified_version):
        findings.append('every skill\'s "last_verified" is the 2026-10-04 metadata check, not a capability run')
    return findings


def audit(env: Mapping[str, str] | None = None) -> list[Row]:
    statuses = _registry_statuses()
    return [audit_role(r, env, statuses.get(r.registry_key) if r.registry_key else None) for r in CATALOG]


def skill_rows() -> list[list[str]]:
    """Runtime skills (omni_prod.skills_runtime): code exists and is injected
    into the named roles' prompts (CONNECTED); VERIFIED needs live evidence."""
    from .runtime_bindings import SKILL_BY_KEY
    from .skills_runtime import WEB_SKILLS
    rows = []
    for skill in WEB_SKILLS:
        b = SKILL_BY_KEY.get(skill.key)
        live = [e for e in (b.evidence if b else ()) if e.kind == 'live']
        rows.append([f'{skill.key}@{skill.version}', VERIFIED if live else CONNECTED,
                     'omni_prod.skills_runtime' + (' + static checks' if skill.static_checks else ''),
                     'injected into: ' + ', '.join(skill.roles),
                     'live (web)' if live else 'unit tests only',
                     '; '.join(e.ref + (f' — {e.note}' if e.note else '') for e in (b.evidence if b else ())) or 'tests/test_skills_runtime_and_review.py',
                     'part of the build call (longer prompts/code)',
                     '; '.join(b.gaps) if b and b.gaps else '—'])
    return rows


def markdown(rows: list[Row], findings: list[str]) -> str:
    def cell(text):
        return str(text).replace('|', '/').replace('\n', ' ')
    counts = {k: sum(1 for r in rows if r.lifecycle == k) for k in ORDER}
    out = ['# Agent/Skill status — computed by `python -m omni_prod.registry_audit --write`', '',
           'Generated from `omni_prod/agent_catalog.py` (what the founder spec defines) and '
           '`omni_prod/runtime_bindings.py` (what runs, with evidence). Do not edit by hand.', '',
           'Lifecycle: DEFINED (catalog only) → IMPLEMENTED (code) → CONNECTED (configuration/provider observed) → '
           'VERIFIED (worked in a real run with an id) · BLOCKED (named credential/service missing).', '',
           'Totals: ' + ', '.join(f'{k} {v}' for k, v in counts.items()), '']
    for family in dict.fromkeys(r.role.family for r in rows):
        out += [f'## {family}', '',
                '| Agent | Status | Implementation | Configuration | Verification | Evidence | Cost | Remaining gap |',
                '|---|---|---|---|---|---|---|---|']
        for r in (x for x in rows if x.role.family == family):
            out.append('| ' + ' | '.join(cell(c) for c in (
                f'{r.role.name}', r.lifecycle + (' ⚠' if r.issues else ''), r.implementation, r.configuration,
                r.verification, r.evidence, r.cost, r.gap)) + ' |')
        out.append('')
    out += ['## runtime skills (web)', '',
            '| Skill | Status | Implementation | Configuration | Verification | Evidence | Cost | Remaining gap |',
            '|---|---|---|---|---|---|---|---|']
    out += ['| ' + ' | '.join(cell(c) for c in r) + ' |' for r in skill_rows()] + ['']
    issues = [f'- {r.role.name}: {i}' for r in rows for i in r.issues]
    out += ['## Mismatches found', ''] + (issues or ['- none in agent roles']) + [f'- {f}' for f in findings] + ['']
    return '\n'.join(out)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    rows = audit()
    text = markdown(rows, skill_registry_findings())
    if '--write' in argv:
        path = Path(__file__).resolve().parent.parent / 'docs' / 'AGENT_SKILL_STATUS.md'
        path.write_text(text + '\n', encoding='utf-8')
        print(f'wrote {path}')
    else:
        print(text)
    hard = [i for r in rows for i in r.issues if 'does not import' in i]
    return 1 if hard else 0


if __name__ == '__main__':
    raise SystemExit(main())
